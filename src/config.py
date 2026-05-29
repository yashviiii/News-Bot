"""Centralized configuration and tunable constants.

Values defined here are the locked spec defaults. A handful of operational
knobs (DB path, embedding model name, user agent, log level) may be
overridden via environment variables loaded from .env at startup.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("DB_PATH", str(REPO_ROOT / "news.db"))
SCHEMA_PATH = REPO_ROOT / "schema.sql"

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

NEWS_FETCH_LIMIT = 100
MAX_ATTEMPTS = 100
TARGET_SUCCESS = 10
MIN_COMPANY_MENTIONS = 3
MIN_TEXT_LENGTH = 200
DATE_WINDOW_DAYS = 30
PER_DOMAIN_CAP = 3
HTTP_TIMEOUT_SECONDS = 15
HTTP_MAX_CONCURRENT = 5
HTTP_RETRY_COUNT = 1
USER_AGENT = os.environ.get(
    "USER_AGENT", "NewsIngestionPipeline/0.1 (research project)"
)

PRESS_RELEASE_DOMAINS = {
    "prnewswire.com",
    "businesswire.com",
    "globenewswire.com",
    "newswire.com",
    "marketwired.com",
    "accesswire.com",
}

CHUNK_MIN_TOKENS = 50
CHUNK_MAX_TOKENS = 300

# Upper bound on raw_text length we'll store/embed. Articles longer than this
# are truncated (preserving the head) with a status_reason marker, so the
# pipeline still produces searchable chunks instead of failing or eating RAM.
MAX_ARTICLE_CHARS = 200_000

# Retry policy: which prior `status` values are eligible for a fresh attempt.
# 'ok' / 'filtered' stay deduped (already succeeded, or intentionally rejected
# for content reasons). 'failed' / 'empty' are usually transient.
RETRYABLE_STATUSES = ("failed", "empty")

# Lead section heuristic: paragraphs that begin within this many chars of the
# article start (or within og:description, whichever is longer) get tagged
# "lead" instead of "body".
LEAD_PREFIX_CHARS = 400

EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "BAAI/bge-small-en-v1.5")
EMBED_DIM = 384

GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
)

DEFAULT_SEARCH_K = 10
MAX_SEARCH_K = 100
DEFAULT_THRESHOLD = 0.65
# Per-result tier boundary: chunks scoring above STRONG_THRESHOLD are
# labelled "strong", chunks between DEFAULT_THRESHOLD and STRONG_THRESHOLD
# are labelled "weak" but still returned. Below DEFAULT_THRESHOLD the
# entire result set is suppressed (hide-over-mislead).
STRONG_THRESHOLD = 0.72
# Search-time near-duplicate detection: if two chunks in the result set
# have an embedding cosine ≥ this threshold, the lower-scored one is
# dropped. Catches syndicated boilerplate (e.g. marketbeat.com's "Key
# News" block re-used across many of their articles) that the article-
# level content_hash can't see because the chunks live in different
# articles with different titles + URLs.
DEDUP_COSINE_THRESHOLD = 0.95
RRF_K_CONSTANT = 60
VECTOR_CANDIDATES = 20
BM25_CANDIDATES = 20


def configure_logging() -> None:
    """Apply stdlib logging configuration once at process start."""
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
