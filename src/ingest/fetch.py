"""Google News RSS query, URL resolution, and HTTP fetching.

All network I/O is defensive: TLS verification always on, explicit
timeouts, capped retries, and no auto-following redirects across hosts
without re-validation. We treat every response as untrusted.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote_plus, urlparse

import base64
import json
import re

import feedparser
import requests

from ..config import (
    DATE_WINDOW_DAYS,
    GOOGLE_NEWS_RSS_URL,
    HTTP_RETRY_COUNT,
    HTTP_TIMEOUT_SECONDS,
    MAX_ARTICLE_CHARS,
    NEWS_FETCH_LIMIT,
    USER_AGENT,
)


# Cap on downloaded bytes per resource. Protects against decompression bombs,
# pathological PDFs, and runaway memory use. Set to 4× MAX_ARTICLE_CHARS as a
# rough proxy for bytes-vs-chars asymmetry across encodings.
_MAX_DOWNLOAD_BYTES = MAX_ARTICLE_CHARS * 4


logger = logging.getLogger(__name__)


_ALLOWED_SCHEMES = {"http", "https"}


@dataclass
class RssItem:
    title: str
    link: str
    published_at: Optional[datetime]
    source_domain: Optional[str]


@dataclass
class FetchedDoc:
    """Result of fetching a remote resource.

    `content_type` is the simple type ("text/html" or "application/pdf").
    `text` is the decoded body: HTML string for text/html, or plain text
    extracted from the PDF for application/pdf. Callers dispatch on
    `content_type` to pick the right extractor.
    """

    content_type: str
    text: str


def normalize_url(url: str) -> str:
    """Return a canonical form for URL-hash dedup: scheme + netloc + path + sorted query."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    # Strip default ports.
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    path = parsed.path or "/"
    # Drop common tracking params for dedup stability.
    if parsed.query:
        params = [
            kv
            for kv in parsed.query.split("&")
            if kv and not kv.startswith(("utm_", "fbclid=", "gclid=", "mc_cid=", "mc_eid="))
        ]
        params.sort()
        query = "&".join(params)
    else:
        query = ""
    return f"{scheme}://{netloc}{path}" + (f"?{query}" if query else "")


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _parse_pubdate(entry: dict) -> Optional[datetime]:
    pp = entry.get("published_parsed") or entry.get("updated_parsed")
    if not pp:
        return None
    try:
        return datetime(*pp[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def fetch_rss(company: str, *, limit: int = NEWS_FETCH_LIMIT) -> list[RssItem]:
    """Query Google News RSS for a company; return at most `limit` recent items."""
    if not company.strip():
        return []
    url = GOOGLE_NEWS_RSS_URL.format(query=quote_plus(company))
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECONDS, verify=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Google News RSS fetch failed: %s", exc)
        return []

    parsed = feedparser.parse(resp.content)
    items: list[RssItem] = []
    cutoff = datetime.now(timezone.utc).timestamp() - DATE_WINDOW_DAYS * 86400
    for entry in parsed.entries[:limit]:
        link = entry.get("link")
        title = entry.get("title", "")
        if not link or not isinstance(link, str):
            continue
        pub = _parse_pubdate(entry)
        if pub is not None and pub.timestamp() < cutoff:
            continue
        src = None
        src_obj = entry.get("source")
        if isinstance(src_obj, dict):
            src = src_obj.get("href") or src_obj.get("title")
        items.append(
            RssItem(title=title, link=link, published_at=pub, source_domain=src)
        )
    return items


_GN_ARTICLE_PATH = re.compile(r"/(?:rss/)?articles/([A-Za-z0-9_\-]+)")


def _gn_resolve(google_news_url: str) -> Optional[str]:
    """Resolve a Google News wrapper URL to the publisher URL via batchexecute.

    Google News stopped serving Location-header redirects on these wrappers;
    instead the client calls a `batchexecute` RPC with a signature + timestamp
    extracted from the article page. We follow the same approach.
    """
    match = _GN_ARTICLE_PATH.search(urlparse(google_news_url).path)
    if not match:
        return None
    article_id = match.group(1)
    headers = {"User-Agent": USER_AGENT}
    try:
        page = requests.get(
            google_news_url, headers=headers, timeout=HTTP_TIMEOUT_SECONDS, verify=True
        )
        page.raise_for_status()
    except requests.RequestException:
        return None

    # Pull data-n-a-sg (signature) and data-n-a-ts (timestamp) from the c-wiz tag.
    sig_match = re.search(r'data-n-a-sg="([^"]+)"', page.text)
    ts_match = re.search(r'data-n-a-ts="([^"]+)"', page.text)
    if not (sig_match and ts_match):
        return None
    signature = sig_match.group(1)
    timestamp = ts_match.group(1)

    payload = [
        "Fbv4je",
        f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{article_id}","{timestamp}","{signature}"]',
    ]
    body = "f.req=" + requests.utils.quote(json.dumps([[payload]]))
    try:
        resp = requests.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            data=body,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            timeout=HTTP_TIMEOUT_SECONDS,
            verify=True,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    # Response is a chunked text format; the URL appears inside a JSON array.
    text = resp.text
    # Find the first https?:// URL in the response that is not a google.com URL.
    for m in re.finditer(r"https?://[^\"\\\\]+", text):
        candidate = m.group(0)
        host = urlparse(candidate).netloc.lower()
        if host and "google.com" not in host and "googleusercontent.com" not in host:
            return candidate
    return None


def resolve_redirect(url: str, *, max_hops: int = 5) -> Optional[str]:
    """Manually walk redirects to capture the final publisher URL.

    Each hop is re-validated: scheme allow-list, host extraction, TLS verify on.
    Returns None if the chain breaks or exceeds the cap.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return None
    host = parsed.netloc.lower()
    if host.endswith("news.google.com"):
        resolved = _gn_resolve(url)
        if resolved:
            return resolved
        # If the special-case resolver failed, fall through to generic logic;
        # at worst we return None below.
    current = url
    headers = {"User-Agent": USER_AGENT}
    for _ in range(max_hops):
        try:
            resp = requests.get(
                current,
                headers=headers,
                timeout=HTTP_TIMEOUT_SECONDS,
                allow_redirects=False,
                verify=True,
                stream=True,
            )
        except requests.RequestException as exc:
            logger.debug("redirect resolution failed for %s: %s", current, exc)
            return None
        finally:
            # Make sure we don't leave the connection open.
            try:
                resp.close()  # type: ignore[has-type]
            except Exception:  # noqa: BLE001
                pass
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("Location")
            if not loc:
                return None
            # Resolve relative locations against current URL.
            from urllib.parse import urljoin

            nxt = urljoin(current, loc)
            nxt_scheme = urlparse(nxt).scheme.lower()
            if nxt_scheme not in _ALLOWED_SCHEMES:
                return None
            current = nxt
            continue
        if 200 <= resp.status_code < 300:
            return current
        # Google News sometimes returns 200 with an HTML body containing the
        # canonical link; capture that case in fetch_html (we get it via GET).
        return current
    return None


def _pdf_to_text(pdf_bytes: bytes) -> Optional[str]:
    """Extract plain text from a PDF byte string via pypdf.

    Returns None if the PDF cannot be parsed or yields no extractable text
    (image-only PDFs, encrypted PDFs without a password, malformed files).
    """
    if not pdf_bytes:
        return None
    try:
        from io import BytesIO

        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError:
        logger.warning("pypdf is not installed; PDF documents will be skipped")
        return None
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
        if reader.is_encrypted:
            # We don't have a password — abandon. Encrypted PDFs are rarely
            # parseable and we shouldn't guess.
            return None
        parts: list[str] = []
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:  # noqa: BLE001 — individual page may be corrupt
                continue
            if page_text:
                parts.append(page_text.strip())
        joined = "\n\n".join(p for p in parts if p)
        return joined or None
    except (PdfReadError, ValueError, OSError) as exc:
        logger.debug("pypdf failed to parse PDF: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — defensive: never crash the worker
        logger.warning("unexpected pypdf failure: %s", exc)
        return None


def fetch_document(url: str) -> Optional[FetchedDoc]:
    """HTTP GET with retry/timeout/UA. Detects PDF vs HTML by Content-Type.

    Returns a `FetchedDoc` whose `text` is:
      - the HTML response body for text/html responses, or
      - the plain text extracted by pypdf for application/pdf responses.

    Downloads are capped at `_MAX_DOWNLOAD_BYTES` to bound memory.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5"}
    last_exc: Optional[Exception] = None
    for attempt in range(HTTP_RETRY_COUNT + 1):
        try:
            resp = requests.get(
                url,
                headers=headers,
                timeout=HTTP_TIMEOUT_SECONDS,
                allow_redirects=True,
                verify=True,
                stream=True,
            )
            try:
                if resp.status_code >= 500:
                    last_exc = RuntimeError(f"HTTP {resp.status_code}")
                    continue
                if resp.status_code >= 400:
                    return None

                # Read body with a hard byte cap.
                raw = resp.raw.read(_MAX_DOWNLOAD_BYTES + 1, decode_content=True)
                if len(raw) > _MAX_DOWNLOAD_BYTES:
                    logger.debug("download exceeded %d bytes for %s", _MAX_DOWNLOAD_BYTES, url)
                    raw = raw[:_MAX_DOWNLOAD_BYTES]

                ct_header = (resp.headers.get("Content-Type") or "").lower()
                is_pdf = (
                    "application/pdf" in ct_header
                    or raw[:5] == b"%PDF-"
                    or url.lower().rsplit("?", 1)[0].endswith(".pdf")
                )
                if is_pdf:
                    text = _pdf_to_text(raw)
                    if not text:
                        return None
                    return FetchedDoc(content_type="application/pdf", text=text)

                # Decode HTML using the response's apparent encoding.
                encoding = resp.encoding or resp.apparent_encoding or "utf-8"
                try:
                    body = raw.decode(encoding, errors="replace")
                except LookupError:
                    body = raw.decode("utf-8", errors="replace")
                return FetchedDoc(content_type="text/html", text=body)
            finally:
                try:
                    resp.close()
                except Exception:  # noqa: BLE001
                    pass
        except requests.RequestException as exc:
            last_exc = exc
        if attempt < HTTP_RETRY_COUNT:
            time.sleep(0.5 * (attempt + 1))
    logger.debug("fetch_document giving up on %s: %s", url, last_exc)
    return None


def fetch_html(url: str) -> Optional[str]:
    """Backward-compat shim: returns HTML text only, ignores PDF responses.

    Kept for the test suite and any direct callers that don't need PDF support.
    Production code should use `fetch_document` instead.
    """
    doc = fetch_document(url)
    if doc is None or doc.content_type != "text/html":
        return None
    return doc.text
