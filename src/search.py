"""Hybrid semantic + BM25 search with Reciprocal Rank Fusion.

Returns a `results` array of source-grounded chunks. When no chunk clears
the cosine `threshold`, `results` is empty and the response carries a
`warning` + `corpus` stats so the caller can see *why* — we deliberately
hide low-confidence chunks rather than return potentially misleading
passages.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from collections import defaultdict
from typing import Optional

import numpy as np

from . import config, db as db_mod
from .ingest import embed
from .ingest.pipeline import _normalize_company


logger = logging.getLogger(__name__)


# FTS5 MATCH special chars to escape by quoting.
_FTS_TOKEN = re.compile(r"\w+", flags=re.UNICODE)


def _build_fts_query(q: str) -> str:
    """Build a safe FTS5 MATCH expression from free-text query.

    FTS5's query language treats characters like `"`, `*`, `(`, `:`, `-` as
    operators. We extract alphanumeric tokens only and OR them together.
    Empty after tokenization → returns a sentinel that matches nothing.
    """
    tokens = _FTS_TOKEN.findall(q)
    if not tokens:
        return '"___no_match___"'
    # Quote each token to disable operator interpretation.
    quoted = [f'"{t}"' for t in tokens]
    return " OR ".join(quoted)


def _lookup_company_id(conn: sqlite3.Connection, company: str) -> Optional[int]:
    norm = _normalize_company(company)
    row = conn.execute(
        "SELECT id FROM companies WHERE normalized_name = ?", (norm,)
    ).fetchone()
    return int(row["id"]) if row else None


def _infer_company_from_query(
    conn: sqlite3.Connection, q: str
) -> Optional[tuple[int, str]]:
    """Pick the company whose normalized name appears in the query, longest match wins.

    Returns (company_id, display_name) or None if no known company is mentioned.
    Match is case-insensitive and substring-based against `normalized_name`,
    which is already lowercased + whitespace-collapsed in the pipeline. Tie-
    breaking by longest name handles cases like 'Tesla Motors' vs 'Tesla'.
    """
    if not q:
        return None
    norm_query = _normalize_company(q)
    if not norm_query:
        return None
    rows = conn.execute(
        "SELECT id, name, normalized_name FROM companies"
    ).fetchall()
    best: Optional[tuple[int, int, str]] = None  # (length, id, display_name)
    for r in rows:
        n = r["normalized_name"]
        if not n:
            continue
        # Require a word-boundary-ish match: name must appear bracketed by
        # non-alphanumerics or string edges to avoid 'apple' inside 'pineapple'.
        if not re.search(rf"(?:^|\W){re.escape(n)}(?:\W|$)", norm_query):
            continue
        if best is None or len(n) > best[0]:
            best = (len(n), int(r["id"]), r["name"])
    if best is None:
        return None
    return best[1], best[2]


def _corpus_stats(conn: sqlite3.Connection, company_id: int) -> dict:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n,
               MIN(published_at) AS dmin,
               MAX(published_at) AS dmax
        FROM articles
        WHERE company_id = ? AND status = 'ok'
        """,
        (company_id,),
    ).fetchone()
    sources_rows = conn.execute(
        """
        SELECT DISTINCT source_domain FROM articles
        WHERE company_id = ? AND status = 'ok' AND source_domain IS NOT NULL
        ORDER BY source_domain
        """,
        (company_id,),
    ).fetchall()
    sources = [r["source_domain"] for r in sources_rows if r["source_domain"]]
    return {
        "articles_searched": int(row["n"] or 0),
        "date_range": [row["dmin"], row["dmax"]],
        "sources": sources,
    }


def _vector_search(
    conn: sqlite3.Connection, company_id: int, query_vec: np.ndarray, *, top: int
) -> list[tuple[int, float]]:
    rows = conn.execute(
        """
        SELECT chunks.id AS id, chunks.embedding AS embedding
        FROM chunks
        JOIN articles ON articles.id = chunks.article_id
        WHERE articles.company_id = ? AND articles.status = 'ok'
        """,
        (company_id,),
    ).fetchall()
    if not rows:
        return []
    ids = np.array([r["id"] for r in rows], dtype=np.int64)
    matrix = np.stack(
        [np.frombuffer(r["embedding"], dtype=np.float32) for r in rows], axis=0
    )
    # Both sides are pre-normalized → dot product is cosine.
    q = query_vec.astype(np.float32)
    qn = q / (np.linalg.norm(q) + 1e-12)
    scores = matrix @ qn
    order = np.argsort(-scores)[:top]
    return [(int(ids[i]), float(scores[i])) for i in order]


def _bm25_search(
    conn: sqlite3.Connection, company_id: int, q: str, *, top: int
) -> list[int]:
    match_expr = _build_fts_query(q)
    rows = conn.execute(
        """
        SELECT chunks.id AS id
        FROM chunks_fts
        JOIN chunks ON chunks.id = chunks_fts.rowid
        JOIN articles ON articles.id = chunks.article_id
        WHERE chunks_fts MATCH ?
          AND articles.company_id = ?
          AND articles.status = 'ok'
        ORDER BY rank
        LIMIT ?
        """,
        (match_expr, company_id, top),
    ).fetchall()
    return [int(r["id"]) for r in rows]


def _rrf(
    vector_ranked: list[int], bm25_ranked: list[int], *, k_const: int = config.RRF_K_CONSTANT
) -> dict[int, float]:
    scores: dict[int, float] = defaultdict(float)
    for rank, cid in enumerate(vector_ranked):
        scores[cid] += 1.0 / (k_const + rank + 1)
    for rank, cid in enumerate(bm25_ranked):
        scores[cid] += 1.0 / (k_const + rank + 1)
    return scores


def _fetch_chunk_details(
    conn: sqlite3.Connection, chunk_ids: list[int]
) -> dict[int, dict]:
    if not chunk_ids:
        return {}
    placeholders = ",".join("?" * len(chunk_ids))
    rows = conn.execute(
        f"""
        SELECT
          chunks.id AS chunk_id,
          chunks.text AS chunk_text,
          chunks.section AS section,
          chunks.char_start AS char_start,
          chunks.char_end AS char_end,
          chunks.chunk_index AS chunk_index,
          articles.id AS article_id,
          articles.url AS url,
          articles.title AS title,
          articles.published_at AS published_at,
          articles.source_domain AS source_domain
        FROM chunks
        JOIN articles ON articles.id = chunks.article_id
        WHERE chunks.id IN ({placeholders})
        """,
        chunk_ids,
    ).fetchall()
    return {int(r["chunk_id"]): dict(r) for r in rows}


def search(
    company: Optional[str],
    q: str,
    *,
    k: int = config.DEFAULT_SEARCH_K,
    threshold: float = config.DEFAULT_THRESHOLD,
    vector_only: bool = False,
    db_path: Optional[str] = None,
) -> dict:
    """Run hybrid (default) or cosine-only search.

    `vector_only=False` (default): run BM25 in parallel with cosine and merge
    the two rankings with Reciprocal Rank Fusion. Hybrid is robust against
    queries that lean on rare keyword tokens (tickers, model numbers,
    proper nouns) where dense embeddings alone can miss exact matches.

    `vector_only=True`: rank purely by cosine similarity over the chunk
    embeddings. Faster and avoids BM25's keyword bias; useful for paraphrase-
    style queries.

    `company` may be None — in that case the query is scanned for any known
    company name and the longest match wins. The resolved company is echoed
    back in the response as `company` plus `company_inferred=True`.
    """
    if not q or not q.strip():
        raise ValueError("query parameter required")
    if k <= 0 or k > config.MAX_SEARCH_K:
        raise ValueError(f"k must be in 1..{config.MAX_SEARCH_K}")

    inferred = False
    with db_mod.connect(db_path) as conn:
        if company and company.strip():
            company_id = _lookup_company_id(conn, company)
            company_used = company
            if company_id is None:
                return {"_not_found": company}
        else:
            guess = _infer_company_from_query(conn, q)
            if guess is None:
                return {
                    "_infer_failed": True,
                    "query": q,
                    "message": (
                        "No company provided and none could be inferred from "
                        "the query. Add a company name to your query (e.g. "
                        "'Tesla Roadster …') or pass the company= parameter."
                    ),
                }
            company_id, company_used = guess
            inferred = True

        corpus = _corpus_stats(conn, company_id)

        query_vec = embed.embed_one(q)
        vector_hits = _vector_search(
            conn, company_id, query_vec, top=config.VECTOR_CANDIDATES
        )
        cosine_by_id: dict[int, float] = {cid: score for cid, score in vector_hits}

        if not vector_hits:
            return {
                "query": q,
                "company": company_used,
                "company_inferred": inferred,
                "mode": "cosine" if vector_only else "hybrid",
                "results": [],
                "tier_summary": {
                    "strong": 0, "weak": 0,
                    "strong_threshold": config.STRONG_THRESHOLD,
                    "relevance_threshold": threshold,
                },
                "warning": "No matching chunks for this company/query.",
                "corpus": corpus,
                "source_coverage": _summarize_source_coverage([]),
                "suggestion": (
                    f"Run /ingest?company={company_used} first or refine your query."
                ),
            }

        if vector_only:
            # Pure cosine: top-K from the already-sorted vector hit list.
            top_pairs: list[tuple[int, float]] = vector_hits[:k]
            rrf_score_map: dict[int, Optional[float]] = {cid: None for cid, _ in top_pairs}
        else:
            bm25_hits = _bm25_search(conn, company_id, q, top=config.BM25_CANDIDATES)
            vector_ranked = [cid for cid, _ in vector_hits]
            rrf_scores = _rrf(vector_ranked, bm25_hits)
            if not rrf_scores:
                return {
                    "query": q,
                    "company": company_used,
                    "company_inferred": inferred,
                    "mode": "hybrid",
                    "results": [],
                    "tier_summary": {
                        "strong": 0, "weak": 0,
                        "strong_threshold": config.STRONG_THRESHOLD,
                        "relevance_threshold": threshold,
                    },
                    "warning": "No matching chunks for this company/query.",
                    "corpus": corpus,
                    "source_coverage": _summarize_source_coverage([]),
                    "suggestion": (
                        f"Run /ingest?company={company_used} first or refine your query."
                    ),
                }
            top_pairs = sorted(rrf_scores.items(), key=lambda x: -x[1])[:k]
            rrf_score_map = {cid: score for cid, score in top_pairs}

        details = _fetch_chunk_details(conn, [cid for cid, _ in top_pairs])

        results: list[dict] = []
        for cid, _primary in top_pairs:
            d = details.get(cid)
            if d is None:
                continue
            cos = cosine_by_id.get(cid)
            rrf_val = rrf_score_map.get(cid)
            # Per-chunk confidence tier. Calling this "weak" surfaces the
            # uncertainty inline with the data rather than burying it in a
            # numeric score the consumer might overlook.
            if cos is None:
                tier = "weak"
            elif cos >= config.STRONG_THRESHOLD:
                tier = "strong"
            else:
                tier = "weak"
            results.append(
                {
                    "tier": tier,
                    "rrf_score": (round(rrf_val, 6) if rrf_val is not None else None),
                    "cosine_score": (round(cos, 4) if cos is not None else None),
                    "chunk_text": d["chunk_text"],
                    "section": d["section"],
                    "char_start": d["char_start"],
                    "char_end": d["char_end"],
                    "chunk_index": d["chunk_index"],
                    "source": {
                        "article_id": d["article_id"],
                        "url": d["url"],
                        "title": d["title"],
                        "published_at": d["published_at"],
                        "source_domain": d["source_domain"],
                    },
                }
            )

        top_cosine = max(
            (r["cosine_score"] for r in results if r["cosine_score"] is not None),
            default=None,
        )

        mode = "cosine" if vector_only else "hybrid"
        tier_summary = {
            "strong": sum(1 for r in results if r["tier"] == "strong"),
            "weak": sum(1 for r in results if r["tier"] == "weak"),
            "strong_threshold": config.STRONG_THRESHOLD,
            "relevance_threshold": threshold,
        }

        if top_cosine is None or top_cosine < threshold:
            # Hide-over-mislead: when no chunk clears the threshold we return
            # an empty `results` array rather than surface low-confidence
            # chunks. Returning passages that the system itself flagged as
            # weak invites the consumer (human or LLM) to over-trust them.
            # The warning + corpus stats still ship so the caller can see
            # *why* the result set is empty.
            # When we hide, tier_summary reflects what was *returned* (zero)
            # — not the count of suppressed candidates. Otherwise a curious
            # caller reads "weak=10" alongside an empty list and gets confused.
            return {
                "query": q,
                "company": company_used,
                "company_inferred": inferred,
                "mode": mode,
                "results": [],
                "tier_summary": {
                    "strong": 0, "weak": 0,
                    "strong_threshold": config.STRONG_THRESHOLD,
                    "relevance_threshold": threshold,
                },
                "warning": (
                    f"No chunks scored above relevance threshold ({threshold:.2f}). "
                    f"Top cosine match was {top_cosine if top_cosine is not None else 0:.2f}"
                    " — the topic appears to be outside the scope of stored articles. "
                    "Returning no results rather than low-confidence passages."
                ),
                "corpus": corpus,
                "source_coverage": _summarize_source_coverage([]),
                "suggestion": (
                    f"Try re-running /ingest?company={company_used} for newer articles, "
                    "or refine your query."
                ),
            }

        response = {
            "query": q,
            "company": company_used,
            "company_inferred": inferred,
            "mode": mode,
            "results": results,
            "tier_summary": tier_summary,
            "corpus": corpus,
            "source_coverage": _summarize_source_coverage(results),
        }
        if tier_summary["weak"] > 0:
            response["weak_match_note"] = (
                f"{tier_summary['weak']} of {len(results)} returned chunks fall in the "
                f"weak band ({threshold:.2f} ≤ cosine < {config.STRONG_THRESHOLD:.2f}) "
                "— interpret with caution. They're shown because the query has at least "
                "one strong match in the result set."
            )
        return response


def _summarize_source_coverage(results: list[dict]) -> dict:
    """Group result chunks by source domain so callers can see, at a glance,
    whether a query is covered by one source or by multiple.

    Returns a dict with:
      - `n_sources`: distinct source domains in the result set
      - `n_articles`: distinct articles in the result set
      - `multi_source`: True iff ≥2 distinct sources contributed
      - `note`: a short human-readable string about the coverage shape
      - `per_source`: [{ source_domain, n_chunks, articles: [{id, title}] }]
        sorted by n_chunks descending.

    For conflict-handling: when multi_source is True, the caller knows the
    same query pulled chunks from independent outlets. The chunks themselves
    are still returned verbatim so the caller can compare framings — we don't
    make a claim about whether the sources actually disagree (that requires
    an LLM), only that they exist and what they cover.
    """
    if not results:
        return {
            "n_sources": 0,
            "n_articles": 0,
            "multi_source": False,
            "note": "No results to summarize.",
            "per_source": [],
        }
    by_domain: dict[str, dict] = {}
    article_ids: set[int] = set()
    for r in results:
        src = r.get("source") or {}
        domain = src.get("source_domain") or "(unknown)"
        article_id = src.get("article_id")
        if article_id is not None:
            article_ids.add(int(article_id))
        bucket = by_domain.setdefault(
            domain,
            {"source_domain": domain, "n_chunks": 0, "articles": {}},
        )
        bucket["n_chunks"] += 1
        if article_id is not None and article_id not in bucket["articles"]:
            bucket["articles"][article_id] = {
                "article_id": article_id,
                "title": src.get("title"),
                "url": src.get("url"),
            }
    per_source = []
    for entry in sorted(by_domain.values(), key=lambda b: -b["n_chunks"]):
        per_source.append(
            {
                "source_domain": entry["source_domain"],
                "n_chunks": entry["n_chunks"],
                "articles": list(entry["articles"].values()),
            }
        )
    n_sources = len(per_source)
    multi = n_sources >= 2
    if multi:
        note = (
            f"{n_sources} independent sources cover this query "
            f"({len(article_ids)} articles, {sum(p['n_chunks'] for p in per_source)} chunks). "
            "Compare each chunk's text + source attribution — framings may differ."
        )
    else:
        note = (
            f"Only one source contributed to the top results "
            f"({per_source[0]['source_domain']}, {per_source[0]['n_chunks']} chunks). "
            "Independent corroboration is not available from the current corpus."
        )
    return {
        "n_sources": n_sources,
        "n_articles": len(article_ids),
        "multi_source": multi,
        "note": note,
        "per_source": per_source,
    }
