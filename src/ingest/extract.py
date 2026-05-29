"""Trafilatura wrapper.

Returns the frozen plain-text body plus a list of structural spans
(`(section, char_start, char_end)`) computed against that exact body
string, and basic metadata (title, author, published_at, language).

The structural spans are aligned to `raw_text` by re-finding each
tag's plain-text payload inside the body. This keeps the chunker's
offset invariant intact.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
from xml.etree import ElementTree as ET

import trafilatura
from trafilatura.settings import use_config

from ..config import LEAD_PREFIX_CHARS


logger = logging.getLogger(__name__)


_TF_CONFIG = use_config()
_TF_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")

# Trafilatura XML tags we recognize as sections.
_HEAD_TAGS = {"head"}
_QUOTE_TAGS = {"quote"}


@dataclass
class ExtractionResult:
    raw_text: str
    structural_spans: list[tuple[str, int, int]] = field(default_factory=list)
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None


def _collect_paragraphs(root: ET.Element) -> list[tuple[str, str]]:
    """Walk the trafilatura XML and yield (section, text) for each block.

    Sections: 'title' for <head>, 'quote' for <quote>, 'body' for everything
    else. Lead-vs-body distinction is applied in a second pass against the
    frozen raw_text so it can use og:description + prefix-window heuristics.
    """
    out: list[tuple[str, str]] = []
    for elem in root.iter():
        tag = elem.tag.lower() if isinstance(elem.tag, str) else ""
        text = "".join(elem.itertext()).strip() if elem.text or len(elem) else ""
        if not text:
            continue
        if tag in _HEAD_TAGS:
            out.append(("title", text))
        elif tag in _QUOTE_TAGS:
            out.append(("quote", text))
        elif tag == "p":
            out.append(("body", text))
    return out


def _assign_lead(
    spans: list[tuple[str, int, int]],
    raw_text: str,
    description: Optional[str],
) -> list[tuple[str, int, int]]:
    """Promote early body paragraphs to 'lead'.

    A body span starting before `boundary` chars into raw_text is reclassified
    as 'lead'. `boundary` defaults to LEAD_PREFIX_CHARS, but is extended to the
    end of the og:description string if that string is found verbatim in
    raw_text. This handles outlets whose subdek/description is longer than the
    400-char floor.
    """
    boundary = LEAD_PREFIX_CHARS
    if description:
        desc = description.strip()
        if desc:
            idx = raw_text.find(desc)
            if idx >= 0:
                boundary = max(boundary, idx + len(desc))
    result: list[tuple[str, int, int]] = []
    for tag, start, end in spans:
        if tag == "body" and start < boundary:
            result.append(("lead", start, end))
        else:
            result.append((tag, start, end))
    return result


def _build_spans(raw_text: str, blocks: list[tuple[str, str]]) -> list[tuple[str, int, int]]:
    """Locate each (section, text) block inside raw_text and return spans."""
    spans: list[tuple[str, int, int]] = []
    cursor = 0
    for section, text in blocks:
        # Search starting at cursor; if not found, search globally as a fallback.
        idx = raw_text.find(text, cursor)
        if idx < 0:
            idx = raw_text.find(text)
        if idx < 0:
            continue
        spans.append((section, idx, idx + len(text)))
        cursor = idx + len(text)
    return spans


def extract(html: str) -> Optional[ExtractionResult]:
    """Extract article body + metadata. Returns None if extraction fails."""
    if not html:
        return None
    try:
        text_body = trafilatura.extract(
            html,
            output_format="txt",
            include_comments=False,
            include_tables=False,
            favor_recall=True,
            config=_TF_CONFIG,
        )
    except Exception as exc:  # noqa: BLE001 — defensive: must not crash pipeline
        logger.warning("trafilatura plain extract failed: %s", exc)
        text_body = None
    if not text_body:
        return None

    raw_text: str = text_body

    spans: list[tuple[str, int, int]] = []
    try:
        xml_body = trafilatura.extract(
            html,
            output_format="xml",
            include_comments=False,
            include_tables=False,
            favor_recall=True,
            config=_TF_CONFIG,
        )
        if xml_body:
            root = ET.fromstring(xml_body)
            blocks = _collect_paragraphs(root)
            spans = _build_spans(raw_text, blocks)
    except Exception as exc:  # noqa: BLE001
        logger.debug("structural span extraction failed: %s", exc)

    title = None
    author = None
    published_at = None
    language = None
    description = None
    try:
        meta = trafilatura.extract_metadata(html)
        if meta is not None:
            title = (meta.title or None) if hasattr(meta, "title") else None
            author = (meta.author or None) if hasattr(meta, "author") else None
            published_at = (meta.date or None) if hasattr(meta, "date") else None
            language = (meta.language or None) if hasattr(meta, "language") else None
            description = (meta.description or None) if hasattr(meta, "description") else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("metadata extraction failed: %s", exc)

    spans = _assign_lead(spans, raw_text, description)

    return ExtractionResult(
        raw_text=raw_text,
        structural_spans=spans,
        title=title,
        author=author,
        published_at=published_at,
        language=language,
        description=description,
    )


def extract_pdf(pdf_text: str) -> Optional[ExtractionResult]:
    """Wrap pre-extracted PDF text into an ExtractionResult.

    PDFs have no DOM, so we can't compute lead/title/quote spans. The whole
    text is tagged as 'body' and lead promotion still applies via the
    LEAD_PREFIX_CHARS rule. The caller is responsible for actually parsing
    PDF bytes (we receive the plain text from `fetch._pdf_to_text`).
    """
    if not pdf_text:
        return None
    # Normalize whitespace at the seams: pypdf often emits hyphenated line
    # breaks ("for-\nmation" → "formation") and stray single newlines inside
    # paragraphs. We don't try to fix every artifact, just the cheapest wins.
    cleaned = pdf_text.replace("-\n", "")
    # Collapse single newlines (not blank-line boundaries) into spaces so the
    # paragraph splitter has something to find.
    import re as _re

    cleaned = _re.sub(r"(?<!\n)\n(?!\n)", " ", cleaned)
    cleaned = _re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    if not cleaned:
        return None

    spans: list[tuple[str, int, int]] = [("body", 0, len(cleaned))]
    spans = _assign_lead(spans, cleaned, description=None)
    return ExtractionResult(
        raw_text=cleaned,
        structural_spans=spans,
        title=None,
        author=None,
        published_at=None,
        language=None,
        description=None,
    )
