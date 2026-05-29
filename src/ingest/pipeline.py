"""End-to-end ingestion orchestrator (§5 of the spec).

Public surface:
    run_ingest(company: str, *, force: bool = False, db_path: Optional[str] = None) -> dict

Behavior beyond the original spec:
- Previously-failed URLs (`status in ('failed', 'empty')`) are retried on the
  next ingest. URLs in `'ok'` or `'filtered'` stay deduped.
- The ok path (insert article + insert chunks) runs inside a single
  transaction so partial state isn't possible.
- Network fetches + extraction run in a bounded thread pool
  (`HTTP_MAX_CONCURRENT`). DB writes stay on the main thread.
- `raw_text` is capped at `MAX_ARTICLE_CHARS`; overflowing articles are
  truncated (head preserved) and tagged with status_reason='ok_truncated'.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

from .. import config, db as db_mod
from . import embed, extract as extractor, fetch
from .chunk import chunk_article
from .extract import ExtractionResult


logger = logging.getLogger(__name__)


@dataclass
class _ProcessResult:
    status: str
    reason: Optional[str] = None
    chunks_created: int = 0
    article_id: Optional[int] = None


@dataclass
class _FetchPayload:
    """Result of the worker stage (network + extraction). DB-free."""

    url: str
    url_hash: str
    domain: str
    html: Optional[str]
    extracted: Optional[ExtractionResult]
    error: Optional[str] = None


def _normalize_company(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _count_mentions(text: str, company: str) -> int:
    if not company:
        return 0
    return len(re.findall(re.escape(company), text, flags=re.IGNORECASE))


def _resolve_company(conn: sqlite3.Connection, name: str) -> int:
    norm = _normalize_company(name)
    if not norm:
        raise ValueError("company name is empty after normalization")
    conn.execute(
        "INSERT OR IGNORE INTO companies (name, normalized_name) VALUES (?, ?)",
        (name.strip(), norm),
    )
    row = conn.execute(
        "SELECT id FROM companies WHERE normalized_name = ?", (norm,)
    ).fetchone()
    return int(row["id"])


def _existing_status(conn: sqlite3.Connection, url_hash: str) -> Optional[str]:
    row = conn.execute(
        "SELECT status FROM articles WHERE url_hash = ? LIMIT 1", (url_hash,)
    ).fetchone()
    return row["status"] if row else None


def _delete_existing(conn: sqlite3.Connection, url_hash: str) -> None:
    """Remove any prior row + its chunks for this url_hash (used on retry)."""
    row = conn.execute(
        "SELECT id FROM articles WHERE url_hash = ?", (url_hash,)
    ).fetchone()
    if not row:
        return
    article_id = int(row["id"])
    # Chunks first (FTS5 triggers fire on chunk DELETE)
    conn.execute("DELETE FROM chunks WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))


def _insert_non_ok(
    conn: sqlite3.Connection,
    *,
    company_id: int,
    url: str,
    url_hash: str,
    status: str,
    reason: str,
    title: Optional[str] = None,
    source_domain: Optional[str] = None,
    raw_text: Optional[str] = None,
    content_hash: Optional[str] = None,
    language: Optional[str] = None,
    author: Optional[str] = None,
    published_at: Optional[str] = None,
) -> Optional[int]:
    """Persist a non-ok article row. Uses INSERT OR REPLACE so retries overwrite."""
    try:
        cur = conn.execute(
            """
            INSERT OR REPLACE INTO articles
              (company_id, url, url_hash, content_hash, title, source_domain,
               author, published_at, language, raw_text, raw_text_length,
               status, status_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                url,
                url_hash,
                content_hash,
                title,
                source_domain,
                author,
                published_at,
                language,
                raw_text,
                len(raw_text) if raw_text else None,
                status,
                reason,
            ),
        )
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return None


def _fetch_and_extract(url: str) -> _FetchPayload:
    """Worker stage: network I/O + extraction. No DB access.

    Dispatches to `extract.extract` for HTML or `extract.extract_pdf` for PDF
    based on the Content-Type detected by `fetch.fetch_document`. Safe to run
    from a ThreadPoolExecutor — does not touch any shared mutable state.
    """
    u_hash = fetch.url_hash(url)
    domain = fetch.extract_domain(url)
    try:
        doc = fetch.fetch_document(url)
    except Exception as exc:  # noqa: BLE001
        return _FetchPayload(
            url=url, url_hash=u_hash, domain=domain,
            html=None, extracted=None, error=f"fetch_exception: {exc!s}"[:500],
        )
    if doc is None:
        return _FetchPayload(
            url=url, url_hash=u_hash, domain=domain,
            html=None, extracted=None, error="http_fetch_failed",
        )
    try:
        if doc.content_type == "application/pdf":
            extracted = extractor.extract_pdf(doc.text)
        else:
            extracted = extractor.extract(doc.text)
    except Exception as exc:  # noqa: BLE001
        return _FetchPayload(
            url=url, url_hash=u_hash, domain=domain,
            html=doc.text, extracted=None, error=f"extract_exception: {exc!s}"[:500],
        )
    return _FetchPayload(
        url=url, url_hash=u_hash, domain=domain,
        html=doc.text, extracted=extracted,
    )


def _persist_payload(
    conn: sqlite3.Connection,
    payload: _FetchPayload,
    *,
    company_id: int,
    company_name: str,
) -> _ProcessResult:
    """DB stage: classify the fetch payload and persist it.

    On the ok path, INSERT article + INSERT chunks runs inside a BEGIN/COMMIT
    so a crash between them can never leave an orphan article.
    """
    url, u_hash, domain = payload.url, payload.url_hash, payload.domain

    # If a prior row exists and is retry-eligible, drop it; otherwise the
    # UNIQUE(url_hash) constraint would block a fresh insert.
    prior = _existing_status(conn, u_hash)
    if prior in config.RETRYABLE_STATUSES:
        _delete_existing(conn, u_hash)

    try:
        if payload.error:
            reason = payload.error
            status = "failed"
            _insert_non_ok(
                conn, company_id=company_id, url=url, url_hash=u_hash,
                source_domain=domain, status=status, reason=reason,
            )
            return _ProcessResult(status=status, reason=reason)

        extracted = payload.extracted
        if extracted is None or not extracted.raw_text:
            _insert_non_ok(
                conn, company_id=company_id, url=url, url_hash=u_hash,
                source_domain=domain, status="empty", reason="extraction_empty",
            )
            return _ProcessResult(status="empty", reason="extraction_empty")

        raw_text = extracted.raw_text
        truncated = False
        if len(raw_text) > config.MAX_ARTICLE_CHARS:
            raw_text = raw_text[: config.MAX_ARTICLE_CHARS]
            truncated = True
            # Trim trailing partial paragraph for cleanliness.
            cut = raw_text.rfind("\n\n")
            if cut > config.MAX_ARTICLE_CHARS // 2:
                raw_text = raw_text[:cut]

        if len(raw_text) < config.MIN_TEXT_LENGTH:
            _insert_non_ok(
                conn, company_id=company_id, url=url, url_hash=u_hash,
                source_domain=domain, status="empty", reason="too_short",
                title=extracted.title, raw_text=raw_text,
                language=extracted.language, author=extracted.author,
                published_at=extracted.published_at,
            )
            return _ProcessResult(status="empty", reason="too_short")

        if extracted.language and extracted.language.lower() not in ("en", "english"):
            _insert_non_ok(
                conn, company_id=company_id, url=url, url_hash=u_hash,
                source_domain=domain, status="filtered", reason="non-english",
                title=extracted.title, raw_text=raw_text,
                language=extracted.language, author=extracted.author,
                published_at=extracted.published_at,
            )
            return _ProcessResult(status="filtered", reason="non-english")

        mentions = _count_mentions(raw_text, company_name)
        if mentions < config.MIN_COMPANY_MENTIONS:
            _insert_non_ok(
                conn, company_id=company_id, url=url, url_hash=u_hash,
                source_domain=domain, status="filtered",
                reason="mentioned-in-passing",
                title=extracted.title, raw_text=raw_text,
                language=extracted.language, author=extracted.author,
                published_at=extracted.published_at,
            )
            return _ProcessResult(status="filtered", reason="mentioned-in-passing")

        c_hash = fetch.content_hash(raw_text)
        dup = conn.execute(
            "SELECT 1 FROM articles WHERE content_hash = ? AND status='ok' LIMIT 1",
            (c_hash,),
        ).fetchone()
        if dup is not None:
            _insert_non_ok(
                conn, company_id=company_id, url=url, url_hash=u_hash,
                source_domain=domain, status="filtered",
                reason="duplicate-content",
                title=extracted.title, content_hash=c_hash, raw_text=raw_text,
                language=extracted.language, author=extracted.author,
                published_at=extracted.published_at,
            )
            return _ProcessResult(status="filtered", reason="duplicate-content")

        # ---- ok path: article + chunks in one transaction ----
        chunks = chunk_article(raw_text, extracted.structural_spans or [])
        vectors = embed.embed_texts([c.text for c in chunks]) if chunks else None

        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(
                """
                INSERT INTO articles
                  (company_id, url, url_hash, content_hash, title, source_domain,
                   author, published_at, language, raw_text, raw_text_length,
                   status, status_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?)
                """,
                (
                    company_id, url, u_hash, c_hash, extracted.title, domain,
                    extracted.author, extracted.published_at, extracted.language,
                    raw_text, len(raw_text),
                    "ok_truncated" if truncated else None,
                ),
            )
            article_id = int(cur.lastrowid)
            if chunks:
                rows = [
                    (article_id, c.chunk_index, c.text, c.char_start, c.char_end,
                     c.section, c.token_count, embed.serialize(vec))
                    for c, vec in zip(chunks, vectors)
                ]
                conn.executemany(
                    """
                    INSERT INTO chunks
                      (article_id, chunk_index, text, char_start, char_end,
                       section, token_count, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        return _ProcessResult(
            status="ok", chunks_created=len(chunks), article_id=article_id
        )

    except sqlite3.IntegrityError as exc:
        logger.warning("integrity error for %s: %s", url, exc)
        return _ProcessResult(status="failed", reason="integrity_error")
    except Exception as exc:  # noqa: BLE001
        logger.exception("unhandled error persisting %s", url)
        _insert_non_ok(
            conn, company_id=company_id, url=url, url_hash=u_hash,
            source_domain=domain, status="failed", reason=str(exc)[:500],
        )
        return _ProcessResult(status="failed", reason=str(exc)[:500])


def _build_candidate_list(
    conn: sqlite3.Connection,
    rss_items: list[fetch.RssItem],
    *,
    force: bool,
    summary: dict,
) -> list[str]:
    """Resolve, dedupe, and filter candidate URLs. Returns ordered candidate list.

    Redirect resolution is parallelized — Google News batchexecute calls take
    2-3 s each and dominate wall time otherwise. We preserve the RSS ordering
    of the returned list because downstream relies on it for per-domain
    diversity decisions.
    """
    resolve_workers = max(1, min(config.HTTP_MAX_CONCURRENT, len(rss_items) or 1))
    with ThreadPoolExecutor(max_workers=resolve_workers) as ex:
        resolved_in_order = list(
            ex.map(lambda it: fetch.resolve_redirect(it.link), rss_items)
        )

    candidates: list[str] = []
    seen: set[str] = set()
    for resolved in resolved_in_order:
        if not resolved:
            continue
        domain = fetch.extract_domain(resolved)
        if domain in config.PRESS_RELEASE_DOMAINS:
            continue
        u_hash = fetch.url_hash(resolved)
        if u_hash in seen:
            continue
        seen.add(u_hash)
        if not force:
            existing = _existing_status(conn, u_hash)
            if existing is not None and existing not in config.RETRYABLE_STATUSES:
                summary["skipped_duplicate"] += 1
                continue
        candidates.append(resolved)
    return candidates


def run_ingest(
    company: str, *, force: bool = False, db_path: Optional[str] = None
) -> dict:
    """Run the full ingestion pipeline for a company. Returns the summary dict from §5."""
    if not company or not company.strip():
        raise ValueError("company is required")

    summary = {
        "company": company,
        "company_id": None,
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "empty": 0,
        "filtered": 0,
        "skipped_duplicate": 0,
        "chunks_created": 0,
        "note": None,
    }

    with db_mod.connect(db_path) as conn:
        company_id = _resolve_company(conn, company)
        summary["company_id"] = company_id

        rss_items = fetch.fetch_rss(company)
        logger.info("RSS returned %d items for %s", len(rss_items), company)
        if not rss_items:
            summary["note"] = (
                f"No articles found for '{company}'. Try a more specific name "
                "or check spelling — this may not be a recognized company."
            )
            return summary

        candidate_urls = _build_candidate_list(
            conn, rss_items, force=force, summary=summary
        )

        per_domain_count: dict[str, int] = defaultdict(int)
        attempted = 0
        successful = 0

        # Concurrent fetch + extract; serial DB persistence on the main thread.
        max_workers = max(1, min(config.HTTP_MAX_CONCURRENT, len(candidate_urls) or 1))
        url_iter = iter(candidate_urls)

        def _pre_filter(url: str) -> bool:
            return per_domain_count[fetch.extract_domain(url)] < config.PER_DOMAIN_CAP

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            in_flight: dict = {}

            def _submit_next() -> bool:
                while True:
                    url = next(url_iter, None)
                    if url is None:
                        return False
                    if not _pre_filter(url):
                        continue
                    fut = ex.submit(_fetch_and_extract, url)
                    in_flight[fut] = url
                    return True

            # Prime the pump.
            for _ in range(max_workers):
                if attempted + len(in_flight) >= config.MAX_ATTEMPTS:
                    break
                if successful >= config.TARGET_SUCCESS:
                    break
                if not _submit_next():
                    break

            while in_flight:
                done_fut = next(as_completed(in_flight))
                url = in_flight.pop(done_fut)
                payload = done_fut.result()

                # Apply per-domain cap on completed result (post-network).
                if per_domain_count[payload.domain] >= config.PER_DOMAIN_CAP:
                    # Don't count toward attempted; move on.
                    if successful < config.TARGET_SUCCESS and attempted < config.MAX_ATTEMPTS:
                        _submit_next()
                    continue

                attempted += 1
                result = _persist_payload(
                    conn,
                    payload,
                    company_id=company_id,
                    company_name=company,
                )
                if result.status == "ok":
                    successful += 1
                    per_domain_count[payload.domain] += 1
                    summary["chunks_created"] += result.chunks_created
                elif result.status == "failed":
                    summary["failed"] += 1
                elif result.status == "empty":
                    summary["empty"] += 1
                elif result.status == "filtered":
                    summary["filtered"] += 1

                if (
                    attempted < config.MAX_ATTEMPTS
                    and successful < config.TARGET_SUCCESS
                ):
                    _submit_next()

        summary["attempted"] = attempted
        summary["successful"] = successful

        if attempted >= config.MAX_ATTEMPTS and successful < config.TARGET_SUCCESS:
            summary["note"] = (
                f"Only {successful} articles met quality bar out of "
                f"{attempted} attempts."
            )
        elif not candidate_urls:
            summary["note"] = (
                f"No usable candidate URLs after filtering for '{company}'."
            )

    return summary
