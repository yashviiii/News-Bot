# News Ingestion Pipeline

A local pipeline that, given a company name, ingests recent news, chunks each article with passage-level grounding (every chunk knows its character span in the source text), embeds chunks with [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5), and exposes a hybrid (semantic + BM25 + RRF) search API backed by SQLite.

## Prerequisites

- Python 3.10+
- ~500 MB free disk for the embedding model on first run

## Setup (under 5 minutes)

```bash
git clone <repo> && cd news-pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                # no edits needed for default operation
python -m src.db init               # create fresh DB from schema.sql
```

## Run the API

```bash
uvicorn src.api:app --reload
```

The first request will download the BGE model (~120 MB) and cache it under `~/.cache/huggingface/`.

- UI (Search · Ingest · Companies ingested): <http://localhost:8000/>
- OpenAPI docs: <http://localhost:8000/docs>

## Example invocations

```bash
# Ingest news for any company (GET and POST both accepted)
curl 'http://localhost:8000/ingest?company=Tesla'
curl -X POST 'http://localhost:8000/ingest?company=Tesla'

# Search (company is optional — if omitted, it is inferred from the query
# when a known company name appears in q)
curl 'http://localhost:8000/search?company=Tesla&q=Q3+margins'
curl 'http://localhost:8000/search?q=What+did+Tesla+announce+about+the+Roadster'

# Inspect what was ingested (including failed/empty/filtered)
curl 'http://localhost:8000/articles?company=Tesla'

# List ingested companies
curl 'http://localhost:8000/companies'

# Health check
curl 'http://localhost:8000/health'
```

### `force=true` re-ingestion

`POST /ingest?company=Tesla&force=true` bypasses URL-hash deduplication and re-fetches everything. Without `force`, previously-failed or empty URLs are retried; previously-ok or filtered URLs are skipped.

### PDF support

Articles served as PDFs (detected via Content-Type, the `%PDF-` magic bytes, or a `.pdf` URL suffix) are parsed with `pypdf` and flow through the rest of the pipeline (chunking, embedding, search) identically to HTML.

### `/search` parameters

- `q` (**required**) — the query string. Free text.
- `company` (optional) — restrict to one company. If omitted, the API scans `q` for a known company name and uses that. If nothing matches, the API returns 400.
- `k` (default 10, max 100) — number of top results to return.
- `threshold` (default 0.65) — cosine floor for *any* match. When no chunk scores above this, `results` is empty plus a `warning` explains why. We deliberately return zero results rather than low-confidence chunks (see `decisions.md`).
- Each returned chunk also carries a `"tier"` field: `"strong"` if cosine ≥ 0.72, `"weak"` if 0.65 ≤ cosine < 0.72. Weak chunks come back when at least one strong match exists in the same result set; the response includes a `weak_match_note` so the consumer can interpret them with caution. The `tier_summary` block in the response gives counts plus the actual threshold values used.
- `vector_only` (default `false`) — by default we use hybrid BM25 + RRF over the union of vector + lexical candidates. Set `vector_only=true` to rank purely by cosine similarity (useful for paraphrase-style queries where BM25 noise is unwelcome).

## Sample database

`sample.db` (committed in this repo) is a pre-populated database for **three companies**: Tesla, Apple Inc, and Atlassian. You can skip `/ingest` and go straight to `/search` by pointing the API at it:

```bash
DB_PATH=sample.db uvicorn src.api:app
curl 'http://localhost:8000/search?company=Tesla&q=Where+will+the+Roadster+be+built'
curl 'http://localhost:8000/search?company=Apple+Inc&q=Apple+WWDC+AI+plans'
curl 'http://localhost:8000/search?company=Atlassian&q=Atlassian+restructuring+strategy'
```

See [`examples/search_outputs.md`](examples/search_outputs.md) for **nine** precomputed query outputs — three per company (Tesla, Apple Inc, Atlassian), each demonstrating a clean factual query, a conflict / multi-source query, and an off-topic / weak-match query.

## Further reading

- [`decisions.md`](decisions.md) — design choices and reasoning
- [`Build-bot.md`](../Build-bot.md) — original locked spec this project implements
