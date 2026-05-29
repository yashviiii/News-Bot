"""Chunker correctness, with special focus on char-offset preservation."""

from __future__ import annotations

import pytest

from src.config import CHUNK_MAX_TOKENS, CHUNK_MIN_TOKENS
from src.ingest.chunk import chunk_article


def test_offsets_reproduce_chunk_text():
    raw = (
        "First paragraph that is fairly short.\n\n"
        "Second paragraph that has a bit more content but is still short enough "
        "to potentially merge with neighbors.\n\n"
        "Third paragraph here.\n\n"
        "Fourth and final paragraph closing the article."
    )
    chunks = chunk_article(raw, [])
    assert chunks, "expected at least one chunk"
    for c in chunks:
        assert raw[c.char_start : c.char_end] == c.text


def test_small_paragraphs_merged():
    raw = "Tiny.\n\nAlso tiny.\n\nStill tiny.\n\nFinal tiny sentence."
    chunks = chunk_article(raw, [])
    # Each individual paragraph is < 50 tokens; merge pass should collapse them.
    assert len(chunks) == 1
    assert raw[chunks[0].char_start : chunks[0].char_end] == chunks[0].text


def test_large_paragraph_split_at_sentences():
    sentence = "This is a fairly long sentence that contains a number of words to push token counts higher. "
    big_paragraph = sentence * 40  # ~> CHUNK_MAX_TOKENS
    raw = "Lead paragraph providing context for the story.\n\n" + big_paragraph.strip()
    chunks = chunk_article(raw, [])
    assert len(chunks) >= 2
    for c in chunks:
        assert c.token_count <= CHUNK_MAX_TOKENS + 50  # split target is ~200, allow slack
        assert raw[c.char_start : c.char_end] == c.text


def test_section_tags_propagate_from_structural_spans():
    raw = (
        "Headline article title here.\n\n"
        "Lead paragraph that frames what this story is about and gives the key "
        "reader take-away in the first paragraph as is journalistic convention.\n\n"
        "Body paragraph one with more detail about the story and what happened "
        "and why it matters to readers right now reading the news article.\n\n"
        "Body paragraph two with further analysis and reactions from various "
        "stakeholders quoted within the piece by the reporter who filed it."
    )
    # title=[0,28), lead=[30,~190), body covers the rest
    title_end = raw.find("\n\n", 0)
    lead_start = title_end + 2
    lead_end = raw.find("\n\n", lead_start)
    body_start = lead_end + 2
    body_end = len(raw)
    spans = [
        ("title", 0, title_end),
        ("lead", lead_start, lead_end),
        ("body", body_start, body_end),
    ]
    chunks = chunk_article(raw, spans)
    sections = {c.section for c in chunks}
    # Lead should appear; title may merge into lead due to small token count.
    assert "lead" in sections or "body" in sections


def test_empty_input_returns_empty():
    assert chunk_article("", []) == []
    assert chunk_article("   \n\n  ", []) == []


def test_chunk_indices_are_sequential():
    raw = "\n\n".join(
        f"Paragraph {i} body content with enough words to be meaningful here for sure."
        for i in range(6)
    )
    chunks = chunk_article(raw, [])
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_no_overlap_between_chunks():
    raw = (
        "Alpha paragraph with several words written out for token bulk and substance.\n\n"
        "Beta paragraph following along similarly with additional words and clauses to consume tokens.\n\n"
        "Gamma paragraph again with similar bulk so that none of these get merged together by the chunker."
    )
    chunks = chunk_article(raw, [])
    for prev, nxt in zip(chunks, chunks[1:]):
        assert prev.char_end <= nxt.char_start, (
            f"chunk {prev.chunk_index}.end={prev.char_end} overlaps "
            f"chunk {nxt.chunk_index}.start={nxt.char_start}"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
