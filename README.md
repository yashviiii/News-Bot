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

## Run the app

Start the server with the pre-populated demo DB so you can search immediately:

```bash
DB_PATH=sample.db uvicorn src.api:app
```

Or start with an empty DB and ingest fresh:

```bash
uvicorn src.api:app
```

The first search will download the BGE model (~120 MB) and cache it under `~/.cache/huggingface/`. Open the UI:

> **<http://localhost:8000/>**

The UI is the primary way to drive the system. Three tabs at the top: **Search · Ingest · Companies ingested**.

## Using the UI

### 🔎 Search tab (opens by default)

The Search tab has two sections — a quick-try section at the top for the three pre-ingested sample companies, and a Custom Search panel below for anything else.

**Quick try:**
1. Click one of the three company buttons: **Tesla**, **Apple Inc**, or **Atlassian**.
2. Three sample query cards appear — one *clean factual*, one *multi-source coverage* (good for the conflict-handling test), and one *off-topic / weak* (demonstrates the threshold gate).
3. Click any card to run that query live. The result panel renders below with:
   - A header showing the resolved company + retrieval mode (`hybrid` or `cosine-only`)
   - A **multi-source coverage** banner if more than one outlet contributed
   - Each result chunk as a card with its passage text, source link, publication date, section tag (lead/body/quote), cosine + RRF scores, and a colored **tier badge** — green `strong` (cosine ≥ 0.72) or amber `weak match` (0.65 ≤ cosine < 0.72)

**Custom Search:**
1. Scroll down (or click the **↓ Custom Search** button on the top right of the quick-try panel).
2. **Company** field is optional — it autocompletes from companies already in the DB, but you can also type a new name. If you leave it blank, the system tries to infer the company from your query.
3. **Query** is the only required field.
4. **k** (default 10) and **threshold** (default 0.65) are optional — placeholders show the defaults.
5. **Cosine only** checkbox is unchecked by default — you'll get hybrid BM25 + RRF retrieval. Check it to use pure cosine ranking (useful for paraphrase-style queries).
6. Click **Search**. Same result rendering as the quick-try cards.
7. If you type a company that isn't in the DB, you'll see a friendly error with a clickable "→ ingest XYZ now" link that drops you into the Ingest tab pre-filled.

**Off-topic queries** — when no chunk scores above the threshold, the system returns **zero results** rather than low-confidence chunks. You'll see an amber warning banner explaining the top cosine that was observed, plus corpus stats so you can diagnose whether the topic is outside coverage. This is deliberate — see [`decisions.md`](decisions.md) on the *hide-over-mislead* design choice.

### 📥 Ingest tab

1. Type a company name (any company — the pipeline is not hardcoded).
2. Optionally tick **force** to bypass URL-hash deduplication and re-fetch everything.
3. Click **Ingest**. First run on a new company takes 30 s – 2 min (Google News RSS lookup → URL resolution → article fetches → trafilatura/pypdf extraction → BGE embedding → DB writes, all in a bounded thread pool).
4. When done, the page shows a **summary card** (successful / attempted / failed / empty / filtered / skipped / chunks created) followed by a **list of every successfully ingested article** with its title (clickable to the original source), publishing domain, date, and chunk count.
5. Failed / empty / filtered articles are also persisted in the DB so you can inspect what the pipeline rejected and why — see them via the Companies ingested tab below.

PDFs are handled automatically — if a publisher serves the article as a PDF (detected via Content-Type, `%PDF-` magic bytes, or `.pdf` URL suffix), it's parsed with `pypdf` and flows through the rest of the pipeline identically to HTML.

### 🗂 Companies ingested tab

1. Lists every company in the DB with article count, chunk count, and last-ingested timestamp. **Refresh** button on the right re-fetches after a new ingest.
2. **Click a company name** → drills into that company's articles inline. You see every article (ok / failed / empty / filtered) with status badges, source domain, date, chunk count, and a link to the original.
3. **Status filter** dropdown on the top right lets you focus on a single bucket — useful for debugging ("show me everything that failed").
4. **← Back to companies** returns to the list.

## Sample database

`sample.db` (committed in this repo) is pre-populated with **three companies**: Tesla, Apple Inc, and Atlassian — so you can drive the UI without running an ingest first. Start with `DB_PATH=sample.db uvicorn src.api:app` as shown above.

See [`examples/search_outputs.md`](examples/search_outputs.md) for **nine** precomputed query outputs — three per company, each demonstrating a clean factual query, a conflict / multi-source query, and an off-topic / weak-match query — so you can verify source grounding and the threshold-gate behavior without running anything.

## Further reading

- [`decisions.md`](decisions.md) — design choices and reasoning
