"""Paragraph-based chunker with merge/split.

Computes char offsets against the frozen `raw_text` — slicing
`raw_text[chunk.char_start:chunk.char_end]` always reproduces
`chunk.text` exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import tiktoken

from ..config import CHUNK_MAX_TOKENS, CHUNK_MIN_TOKENS


_PARAGRAPH_SEP = re.compile(r"\n{2,}")
# Sentence end: ., !, or ? followed by whitespace and a capital letter / digit.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_SPLIT_TARGET_TOKENS = 200

_encoder: tiktoken.Encoding | None = None


def _get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


@dataclass
class Chunk:
    text: str
    char_start: int
    char_end: int
    section: str
    chunk_index: int
    token_count: int


def _trim_offsets(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _find_paragraphs(raw_text: str) -> list[tuple[int, int]]:
    """Return (start, end) offsets for each paragraph in raw_text.

    Paragraphs are separated by runs of 2+ newlines. Leading and trailing
    whitespace within a paragraph is trimmed away so offsets point at
    real content.
    """
    paragraphs: list[tuple[int, int]] = []
    cursor = 0
    for match in _PARAGRAPH_SEP.finditer(raw_text):
        s, e = _trim_offsets(raw_text, cursor, match.start())
        if s < e:
            paragraphs.append((s, e))
        cursor = match.end()
    s, e = _trim_offsets(raw_text, cursor, len(raw_text))
    if s < e:
        paragraphs.append((s, e))
    return paragraphs


def _assign_section(
    start: int, end: int, structural_spans: Iterable[tuple[str, int, int]]
) -> str:
    """Pick the structural tag with greatest overlap, default to 'body'."""
    best_section = "body"
    best_overlap = 0
    for tag, s_start, s_end in structural_spans:
        overlap = max(0, min(end, s_end) - max(start, s_start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_section = tag
    return best_section


def _make_segment(
    raw_text: str, start: int, end: int, section: str, encoder: tiktoken.Encoding
) -> dict:
    text = raw_text[start:end]
    return {
        "start": start,
        "end": end,
        "text": text,
        "tokens": len(encoder.encode(text)),
        "section": section,
    }


def _merge_small(
    paragraphs: list[dict], raw_text: str, encoder: tiktoken.Encoding
) -> list[dict]:
    """Merge any paragraph below the min-token floor into a neighbor."""
    result = [dict(p) for p in paragraphs]
    i = 0
    while i < len(result):
        if result[i]["tokens"] >= CHUNK_MIN_TOKENS or len(result) == 1:
            i += 1
            continue
        if i + 1 < len(result):
            # Merge forward: union char range, recompute text+tokens.
            a, b = result[i], result[i + 1]
            section = a["section"] if (a["end"] - a["start"]) >= (b["end"] - b["start"]) else b["section"]
            merged = _make_segment(raw_text, a["start"], b["end"], section, encoder)
            result[i] = merged
            del result[i + 1]
            # Re-check this slot in case still small.
        else:
            # Last and small: merge backward.
            a, b = result[i - 1], result[i]
            section = a["section"] if (a["end"] - a["start"]) >= (b["end"] - b["start"]) else b["section"]
            merged = _make_segment(raw_text, a["start"], b["end"], section, encoder)
            result[i - 1] = merged
            del result[i]
            i -= 1
    return result


def _split_paragraph(
    paragraph: dict, raw_text: str, encoder: tiktoken.Encoding
) -> list[dict]:
    """Split a too-large paragraph at sentence boundaries into ~200-token pieces."""
    p_start = paragraph["start"]
    p_end = paragraph["end"]
    text = paragraph["text"]
    section = paragraph["section"]

    sentence_starts = [0]
    for m in _SENTENCE_BOUNDARY.finditer(text):
        sentence_starts.append(m.end())
    sentence_starts.append(len(text))

    sentences: list[tuple[int, int]] = []
    for i in range(len(sentence_starts) - 1):
        sentences.append((sentence_starts[i], sentence_starts[i + 1]))

    if len(sentences) <= 1:
        # No sentence boundary found; return paragraph as-is to avoid a degenerate
        # single huge chunk being silently truncated.
        return [paragraph]

    groups: list[tuple[int, int]] = []
    cur_start: int | None = None
    cur_end: int | None = None
    cur_tokens = 0
    for s_rel, e_rel in sentences:
        seg_text = text[s_rel:e_rel]
        t = len(encoder.encode(seg_text))
        if cur_start is None:
            cur_start, cur_end, cur_tokens = s_rel, e_rel, t
        elif cur_tokens + t > _SPLIT_TARGET_TOKENS and cur_tokens >= CHUNK_MIN_TOKENS:
            groups.append((cur_start, cur_end))
            cur_start, cur_end, cur_tokens = s_rel, e_rel, t
        else:
            cur_end = e_rel
            cur_tokens += t
    if cur_start is not None:
        groups.append((cur_start, cur_end))

    pieces: list[dict] = []
    for g_start_rel, g_end_rel in groups:
        abs_start = p_start + g_start_rel
        abs_end = p_start + g_end_rel
        abs_start, abs_end = _trim_offsets(raw_text, abs_start, abs_end)
        if abs_start >= abs_end:
            continue
        pieces.append(_make_segment(raw_text, abs_start, abs_end, section, encoder))
    return pieces or [paragraph]


def _split_large(
    paragraphs: list[dict], raw_text: str, encoder: tiktoken.Encoding
) -> list[dict]:
    result: list[dict] = []
    for p in paragraphs:
        if p["tokens"] <= CHUNK_MAX_TOKENS:
            result.append(p)
        else:
            result.extend(_split_paragraph(p, raw_text, encoder))
    return result


def chunk_article(
    raw_text: str, structural_spans: list[tuple[str, int, int]] | None = None
) -> list[Chunk]:
    """Chunk a frozen article body into ordered, offset-bearing chunks."""
    if not raw_text:
        return []

    encoder = _get_encoder()
    spans = structural_spans or []

    paragraph_offsets = _find_paragraphs(raw_text)
    paragraphs: list[dict] = []
    for s, e in paragraph_offsets:
        section = _assign_section(s, e, spans)
        paragraphs.append(_make_segment(raw_text, s, e, section, encoder))

    if not paragraphs:
        return []

    merged = _merge_small(paragraphs, raw_text, encoder)
    final = _split_large(merged, raw_text, encoder)

    chunks: list[Chunk] = []
    for i, p in enumerate(final):
        chunks.append(
            Chunk(
                text=p["text"],
                char_start=p["start"],
                char_end=p["end"],
                section=p["section"],
                chunk_index=i,
                token_count=p["tokens"],
            )
        )
    return chunks
