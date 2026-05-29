"""End-to-end pipeline test with mocked RSS + HTML extraction + embedder."""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from src import config, db as db_mod
from src.ingest import fetch as fetch_mod, pipeline
from src.ingest.extract import ExtractionResult
from src.ingest.fetch import FetchedDoc


COMPANY = "Acme Corp"


def _make_article_text(company: str, idx: int) -> str:
    return (
        f"{company} announces new product, edition {idx}.\n\n"
        f"In a press conference today, {company} confirmed that its newest line "
        "of widgets will ship in Q4 with substantial improvements in efficiency, "
        "reliability, and price competitiveness across the industry segment.\n\n"
        f"Analysts who cover {company} broadly applauded the move, citing the "
        "strength of the order book and recent gains in the company's market "
        "share over the previous twelve months of operations.\n\n"
        "Investors responded positively, with the stock closing up sharply on "
        "elevated trading volumes for the session that just concluded today."
    )


@pytest.fixture()
def tmp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "test.db")
        monkeypatch.setattr(config, "DB_PATH", path)
        db_mod.init_db(path)
        yield path


def _fake_rss_items(n: int = 12) -> list[fetch_mod.RssItem]:
    items = []
    for i in range(n):
        items.append(
            fetch_mod.RssItem(
                title=f"{COMPANY} story {i}",
                link=f"https://news.google.com/articles/article-{i}",
                published_at=datetime.now(timezone.utc),
                source_domain=None,
            )
        )
    return items


def _fake_resolve(url: str) -> str:
    # Map google news wrapper to a per-domain real URL.
    idx = url.rsplit("-", 1)[-1]
    domains = ["reuters.com", "bloomberg.com", "cnbc.com", "wsj.com"]
    return f"https://{domains[int(idx) % len(domains)]}/story-{idx}"


def _fake_fetch_document(url: str) -> FetchedDoc:
    return FetchedDoc(content_type="text/html", text="<html></html>")  # extractor is mocked too


def _fake_fetch_html(url: str) -> str:
    return "<html></html>"  # for any test that still uses the legacy shim


def _fake_extract(html: str) -> ExtractionResult:
    # Counter via closure to vary per-call content.
    idx = _fake_extract._counter  # type: ignore[attr-defined]
    _fake_extract._counter += 1  # type: ignore[attr-defined]
    text = _make_article_text(COMPANY, idx)
    return ExtractionResult(
        raw_text=text,
        structural_spans=[("lead", 0, text.find("\n\n"))],
        title=f"{COMPANY} story {idx}",
        author="Test Author",
        published_at="2026-05-01T00:00:00Z",
        language="en",
    )


_fake_extract._counter = 0  # type: ignore[attr-defined]


def _fake_embed_texts(texts, *, batch_size=32):
    # Deterministic, dimension-correct, L2-normalized vectors.
    rng = np.random.default_rng(seed=42)
    arr = rng.standard_normal((len(texts), config.EMBED_DIM)).astype(np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return arr


def test_run_ingest_end_to_end(tmp_db):
    _fake_extract._counter = 0  # type: ignore[attr-defined]
    with (
        patch.object(pipeline.fetch, "fetch_rss", return_value=_fake_rss_items(12)),
        patch.object(pipeline.fetch, "resolve_redirect", side_effect=_fake_resolve),
        patch.object(pipeline.fetch, "fetch_document", side_effect=_fake_fetch_document),
        patch.object(pipeline.extractor, "extract", side_effect=_fake_extract),
        patch.object(pipeline.embed, "embed_texts", side_effect=_fake_embed_texts),
    ):
        summary = pipeline.run_ingest(COMPANY, db_path=tmp_db)

    assert summary["successful"] >= 1
    assert summary["chunks_created"] >= summary["successful"]

    with sqlite3.connect(tmp_db) as conn:
        conn.row_factory = sqlite3.Row
        ok_rows = conn.execute(
            "SELECT id, raw_text FROM articles WHERE status='ok'"
        ).fetchall()
        assert len(ok_rows) == summary["successful"]
        for art in ok_rows:
            chunks = conn.execute(
                "SELECT char_start, char_end, text FROM chunks WHERE article_id=?",
                (art["id"],),
            ).fetchall()
            assert chunks, f"article {art['id']} produced no chunks"
            for ch in chunks:
                assert (
                    art["raw_text"][ch["char_start"] : ch["char_end"]] == ch["text"]
                ), "char offsets must reproduce chunk.text against article.raw_text"


def test_idempotent_url_hash_dedup(tmp_db):
    _fake_extract._counter = 0  # type: ignore[attr-defined]
    rss = _fake_rss_items(12)
    with (
        patch.object(pipeline.fetch, "fetch_rss", return_value=rss),
        patch.object(pipeline.fetch, "resolve_redirect", side_effect=_fake_resolve),
        patch.object(pipeline.fetch, "fetch_document", side_effect=_fake_fetch_document),
        patch.object(pipeline.extractor, "extract", side_effect=_fake_extract),
        patch.object(pipeline.embed, "embed_texts", side_effect=_fake_embed_texts),
    ):
        first = pipeline.run_ingest(COMPANY, db_path=tmp_db)
        _fake_extract._counter = 0  # type: ignore[attr-defined]
        second = pipeline.run_ingest(COMPANY, db_path=tmp_db)

    assert second["skipped_duplicate"] >= first["successful"]


def test_filter_company_not_mentioned_enough(tmp_db):
    def short_extract(html):
        text = (
            "The market opened higher today on broad strength across sectors.\n\n"
            "Technology shares led the way with double-digit gains for several names. "
            "Investors were optimistic ahead of upcoming earnings season and central "
            "bank meetings scheduled across major economies for next week.\n\n"
            "Volatility eased while bond yields drifted lower modestly across the curve."
        )
        return ExtractionResult(raw_text=text, structural_spans=[], language="en")

    with (
        patch.object(pipeline.fetch, "fetch_rss", return_value=_fake_rss_items(3)),
        patch.object(pipeline.fetch, "resolve_redirect", side_effect=_fake_resolve),
        patch.object(pipeline.fetch, "fetch_document", side_effect=_fake_fetch_document),
        patch.object(pipeline.extractor, "extract", side_effect=short_extract),
        patch.object(pipeline.embed, "embed_texts", side_effect=_fake_embed_texts),
    ):
        summary = pipeline.run_ingest(COMPANY, db_path=tmp_db)

    assert summary["successful"] == 0
    assert summary["filtered"] >= 1


def test_zero_rss_returns_note(tmp_db):
    with patch.object(pipeline.fetch, "fetch_rss", return_value=[]):
        summary = pipeline.run_ingest(COMPANY, db_path=tmp_db)
    assert summary["successful"] == 0
    assert summary["note"] is not None


def test_pdf_document_ingests_via_pypdf_path(tmp_db):
    """A URL whose Content-Type is application/pdf is parsed via pypdf and
    persisted just like an HTML article — same schema, same chunks, same
    offset invariant against raw_text.
    """
    pdf_text = (
        f"{COMPANY} Annual Filing Summary\n\n"
        f"{COMPANY} reported record revenue this period, driven by strength in "
        "its core widget segment and adjacent services. Margins improved across "
        "all reporting units relative to the prior year period reviewed.\n\n"
        f"Management commentary from {COMPANY} executives noted continued "
        "investment in research, manufacturing capacity, and distribution. "
        f"{COMPANY} also reiterated its full-year guidance ranges.\n\n"
        "Analyst notes following the release described the trajectory as "
        "sustainable given current backlog and order book conversion rates."
    )

    def fake_pdf_doc(url: str) -> FetchedDoc:
        return FetchedDoc(content_type="application/pdf", text=pdf_text)

    with (
        patch.object(pipeline.fetch, "fetch_rss", return_value=_fake_rss_items(2)),
        patch.object(pipeline.fetch, "resolve_redirect", side_effect=_fake_resolve),
        patch.object(pipeline.fetch, "fetch_document", side_effect=fake_pdf_doc),
        patch.object(pipeline.embed, "embed_texts", side_effect=_fake_embed_texts),
    ):
        summary = pipeline.run_ingest(COMPANY, db_path=tmp_db)

    assert summary["successful"] >= 1
    assert summary["chunks_created"] >= 1

    with sqlite3.connect(tmp_db) as conn:
        conn.row_factory = sqlite3.Row
        ok_rows = conn.execute(
            "SELECT id, raw_text FROM articles WHERE status='ok'"
        ).fetchall()
        assert ok_rows, "PDF ingest produced no ok articles"
        for art in ok_rows:
            chunks = conn.execute(
                "SELECT char_start, char_end, text, section FROM chunks WHERE article_id=?",
                (art["id"],),
            ).fetchall()
            assert chunks, "PDF article produced no chunks"
            for ch in chunks:
                assert (
                    art["raw_text"][ch["char_start"] : ch["char_end"]] == ch["text"]
                ), "PDF chunks must satisfy the same char-offset invariant as HTML"


def test_pdf_byte_parser_returns_none_for_garbage():
    """fetch._pdf_to_text returns None — not an exception — for non-PDF input."""
    from src.ingest.fetch import _pdf_to_text

    assert _pdf_to_text(b"not a pdf at all") is None
    assert _pdf_to_text(b"") is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
