# Design Decisions

Brief rationale for the architectural choices in this pipeline.

## Chunking strategy and parameters

**Paragraph-based, with merge (< 50 tokens) / split (> 300 tokens), no overlap.**

- **Why paragraphs, not semantic chunking?** News is well-paragraphed by construction. Authors already segment the piece into well structured semantic units. Semantic chunking for this use case would add unncessary time and cost along with errors added from a fidly threshold. Paragraph chunking is also auditable: when asked "why is this chunk what it is?" we point to a paragraph break in the source.
- **Why no overlap?** Paragraph boundaries in news are already coherent. Overlap would dilute chunk embeddings and increase storage with minimal retrieval gain 
- **Split target ~200 tokens.** When a paragraph exceeds the 300-token cap, we pack sentences into ~200-token pieces. This leaves headroom under the cap and avoids pathological one-sentence overshoots.

- **Sentence regex caveat.** The split path uses a regex on `.!?` followed by whitespace+capital/digit/quote. This is intentionally simple. 

## Schema design

Three tables: `companies`, `articles`, `chunks` — plus an FTS5 virtual table for BM25.

- **`articles.raw_text` is load-bearing.** Without storing the frozen extracted string, the char offsets on chunks point to nothing. The chunker's offset invariant — `raw_text[chunk.char_start:chunk.char_end] == chunk.text` — must hold for every chunk so passages can be highlighted exactly in the source.
- **`status` + `status_reason` turn the DB into a debug tool.** Failed, empty, and filtered articles are stored, not silently dropped. `/articles?company=X&status=failed` answers "what did the pipeline try and reject, and why?"
- **Two-layer dedup.** `url_hash` catches re-ingestion attempts (idempotency); `content_hash` catches syndication (Reuters → Yahoo → MSN).
- **Composite index `(company_id, published_at DESC)`** matches the dominant query pattern.
- **`source_domain` denormalized** — extracting from URL in SQL is ugly; one extra column.
- **FTS5 triggers** keep keyword search in sync with `chunks` automatically.

## Source selection

I chose to use a single source (Google News RSS) for articles over multi-source. NewsAPI was considered but article overlap after URL resolution was high enough that the second source mostly produced duplicates. Single-source is simpler with no meaningful coverage loss.

RSS feeds only return the article headline + a wrapper URL (and a publication date). Using that URL the actual content is fetched through a multi-step pipeline:

1. **Redirect resolution** — Google News wrapper URLs unwrapped via `batchexecute` RPC; generic redirects walked manually with re-validated scheme on each hop.
2. **Content download** — TLS-verified GET with retry, timeout, and byte cap. Routed to HTML or PDF by Content-Type / magic bytes / URL suffix.
3. **Extraction** — trafilatura for HTML, pypdf for PDF. Both produce the same `ExtractionResult` (raw_text + structural spans).
4. **Filtering** — empty / short / non-English / mentioned-in-passing / duplicate-content articles persisted with `status` + `status_reason`, never silently dropped.
5. **Chunking + embedding** — paragraph-first merge/split, BGE-small embeddings, article + chunks committed in one per-article transaction.

## Article selection logic

- **30-day window** at the RSS layer
- **Per-domain cap of 3** successful ingestions, for source diversity
- **Press-release wire domains blocked** (`prnewswire.com`, `businesswire.com`, etc.)
- **Company name must appear ≥3 times** in extracted text — filters out "X was mentioned in passing" pieces
- **Min 200 chars** of extracted text — filters paywall/JS-rendered stubs
- **Non-English filtered** with `status='filtered'`, reason `non-english`

**Given more time i would add support for non-english articles to broaden the information scope of the system ans ensure multiple point of views are covered and add Custom ranking instead of trusting Google News ordering — weight by source reputation, recency, content depth.**

## Resilience loop

For every company i chose to target 10 successful ingestions, cap at 100 attempts. Without the cap, an unlucky burst of paywalled URLs would return near-empty data; without the target, we'd silently underfill. The summary surfaces both numbers and emits a `note` when the cap was hit so the caller knows what happened.


## Conflict handling in search

Search results are **not** semantically deduplicated. If a source calls Q3 of a company a "success" and another one calls it a "miss", both surface with full source attribution. 
Semantic dedupe would collapse the conflict and present just one point of view. We leave it up to the human (or LLM) to handle the disagreement.

## Off-topic / weak-match handling

A cosine threshold (default `0.65`) gates relevance. When no chunk in the candidate set scores above the threshold, the response returns an **empty `results` array** plus a `warning` explaining why and a `corpus` stats block showing what was actually searched.

**Why empty over weak.** I chose not to return low-confidence chunks because for a source-grounded retrieval system, surfacing potentially-misleading text is worse than surfacing nothing: a downstream LLM will happily synthesize a confident-sounding answer from any chunks it receives and increase the risk of hallucination. **No documents is a better signal than wrong documents.**

## Vector storage

Float32 numpy arrays serialized to SQLite BLOB, brute-force cosine in-memory. At ~500 chunks per company this is sub-10ms; 

**Given more time i would use a vector db like `sqlite-vec` (or pgvector) to query results** 

## Retry policy

If a company that was ingested before is ingested again with `force=False` the articles that were already ingested are skipped. It is **not** strict idempotency — it's "skip URLs that already produced a usable outcome". URL's whose previous row has status of `ok` or `filtered` are skipped and ones with `status in ('failed', 'empty')` are retried by deleting the prior row inside the per-article transaction and re-inserting. 

This means a transient HTTP 500 or an extractor-empty page doesn't permanently blacklist a URL. `force=True` still bypasses all of this and re-fetches everything.

Given more time i would **Embedding-based dedup** for catching paraphrased syndication. Current `content_hash` dedup catches byte-identical reposts but misses lightly-edited republications across wire services.

## Concurrency

Both the URL-resolution stage (`fetch.resolve_redirect`, which calls Google News `batchexecute`) and the fetch+extract stage run inside a bounded `ThreadPoolExecutor` (`HTTP_MAX_CONCURRENT=5`). The DB persistence stage stays on the main thread because SQLite's single-writer model means parallelizing it gains nothing.

The per-domain cap is checked *after* fetch returns rather than before submission, because we don't increment the cap counter until we get an `ok` result. The cost is occasionally fetching an article we won't use (when prior parallel requests already filled the domain quota); this is small in practice and dramatically simpler than the alternative.


## Article size cap

Each article is capped at `MAX_ARTICLE_CHARS=200_000` to bound embedder time and storage. When truncation occurs, it is trimmed back to the nearest paragraph boundary (if one exists within the second half of the kept text) and tag the row with `status='ok', status_reason='ok_truncated'` so the truncation is visible from `/articles`. Most news articles are 2-15 KB so this cap only kicks in for outlier long-reads.

## Hybrid as default; cosine-only as opt-in

`/search` defaults to **hybrid retrieval**: BM25 + dense-vector cosine candidates merged via Reciprocal Rank Fusion. Cosine-only ranking is one click away in the UI ("Cosine only" checkbox).

**Why hybrid is the default.** Real queries mix concept and keyword. BGE-small handles the concept side well, but rare tokens are where dense embeddings stumble and where BM25 shines. Hybrid is the safer default for a system whose corpus is news — full of named entities, numbers, and exact phrases — because it never silently loses an exact-match hit.

Cosine-only stays available as an option for paraphrase-heavy queries where BM25's keyword bias would surface noise (e.g. a publication name that happens to appear in many unrelated chunks).

## Tiered confidence: strong / weak / hidden

Every returned chunk carries a `tier` field:

| Tier | Cosine band | Behavior |
|---|---|---|
| **strong** | `cosine ≥ 0.72` (`STRONG_THRESHOLD`) | Returned with a green badge in the UI. |
| **weak**   | `0.65 ≤ cosine < 0.72` | Returned **only** when the result set contains at least one strong match. Rendered with an amber `weak match` badge so the consumer can spot them at a glance. The response carries a top-level `weak_match_note` describing how many fell into this band. |
| _(hidden)_ | `cosine < 0.65` (`DEFAULT_THRESHOLD`) | Suppressed entirely. `results` comes back as `[]` plus a warning — see the *Off-topic / weak-match handling* section. |

**Why three bands and not two.** A simple above/below threshold loses information at the edges. A chunk at cosine 0.68 isn't garbage — it's just less confident — and an LLM downstream can use it productively *if* it knows the confidence is reduced. Tagging it `weak` lets the consumer make that call rather than baking the decision into a hard cut. The 0.72 / 0.65 boundaries were picked empirically on this corpus; the constants are in [config.py](src/config.py) so they're easy to recalibrate per deployment.

The `tier_summary` block in every response also reports the actual threshold values used, so an API consumer building their own UI doesn't have to hard-code them.

## Search-time near-duplicate suppression

Article-level `content_hash` catches byte-identical re-posts, but not syndicated boilerplate where outlets reuse the same paragraph across many distinct articles Those chunks slip past ingest-time dedup because the articles themselves are technically different.

**Fix:** at search time, every result set runs through a greedy near-duplicate pass before being returned.

1. Over-fetch `2k` candidates from the ranker (vector-only or hybrid) instead of just `k`.
2. Load the chunks' embeddings from the `chunks.embedding` BLOB column in a single SQL call.
3. Walk candidates in score order. For each chunk, compute cosine vs every already-kept chunk. If the max similarity is `≥ DEDUP_COSINE_THRESHOLD` (0.95), drop the chunk as a near-duplicate of the higher-scored one.
4. Trim survivors to `k`.

Cosine 0.95 was picked empirically — distinct passages on the same topic land around 0.8–0.9, while syndicated copy-paste sits at 0.97+. The threshold lives in [config.py](src/config.py) so it's easy to recalibrate.

The response includes `duplicates_suppressed: <count>` so a consumer can see the dedup pass actually did something (or didn't). Embeddings are L2-normalized at ingest, so the cosine is a plain dot product — cheap enough to run on every search (~400 vector products for default `k=10`).

## PDF support (pypdf fallback)

Some articles are served as PDFs. I added pypdf to parse them. The result flows through the rest of the pipeline identically to HTML.

Kept intentionally simple: no table reconstruction, no layout recovery, no image extraction. Plain prose only.

**Given more time, PDF support would be extended to capture tables and images and analyse them — useful for financial reports and structured filings.**


## Optional search params + company inference

`company`, `k`, and `threshold` are all optional on `/search`. The endpoint only requires query `q`. When `company` is absent, [_infer_company_from_query](src/search.py) scans the `companies` table and picks the longest known company name that appears as a whole word in the query (`re.search(r"(?:^|\W)<name>(?:\W|$)")` against the normalized query, longest match wins to handle "Tesla Motors" vs "Tesla"). The resolved company is returned in the response as `company` plus `company_inferred: true`. This is done to provide more flexibility while querying for the user. If the company is provided it results in more consistent results but the system is equipped to handle empty company name as well

If inference fails (no known company in the query and none provided), the endpoint returns 400 with a message telling the user to either add a company name to the query or pass `company=` explicitly. It is a deliberate choice to not guess across unrelated companies. 

Given more time i would - **MMR re-ranking** to diversify top-K when one article dominates (common when an article has many strong-matching paragraphs).

## Error response shape

FastAPI's built-in `RequestValidationError` defaults to its own 422 schema with a `detail` array of objects (some of which contain non-JSON-serializable `ctx` values). I have chosen to install a global handler in that reshapes those into a structures and consistent format and switches the status to 400. A second handler covers `StarletteHTTPException` for consistency.

## Two major things I would do differently with more time

- **Per-component query decomposition.** A query like *"What did analysts say about Tesla's margins **and** EV competition strategy?"* has two sub-questions; the current system embeds and retrieves on the joint vector and may surface strong results on one sub-question while silently missing the other. Ideally id want decompose multi-part queries and report per-component coverage explicitly.

- **LLM-formatted answers.** The current `/search` endpoint returns the retrieved chunks verbatim — passages from the source articles plus relevance scores and source links. There is no generation step. A natural next layer is an answer-synthesis endpoint (e.g. `POST /answer`) that takes the user's query, passes the top-K retrieved chunks as context to an LLM (Claude / GPT / a local model), and returns a prose answer **with citation markers tying each claim back to the source chunk**. Key design choices we'd lock in: (1) instruct the model to only use information from the supplied chunks and explicitly say "the corpus does not say" when the answer isn't supported, (2) require inline citation markers like `[1]`, `[2]` mapped to `chunk_id`/article URL so every claim is verifiable, (3) keep the raw chunks in the response alongside the synthesized answer so the UI can show both (and so the caller can spot hallucinations). With prompt caching this is also where caching pays for itself — the system prompt + retrieved chunks are stable across follow-up turns.