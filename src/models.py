"""Pydantic response models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    embedding_model: str


class IngestSummary(BaseModel):
    company: str
    company_id: Optional[int] = None
    attempted: int = 0
    successful: int = 0
    failed: int = 0
    empty: int = 0
    filtered: int = 0
    skipped_duplicate: int = 0
    chunks_created: int = 0
    note: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    details: Optional[dict[str, Any]] = None


class CorpusStats(BaseModel):
    articles_searched: int
    date_range: list[Optional[str]]
    sources: list[str]


class SourceRef(BaseModel):
    article_id: int
    url: str
    title: Optional[str]
    published_at: Optional[str]
    source_domain: Optional[str]


class SearchHit(BaseModel):
    rrf_score: float
    cosine_score: Optional[float] = None
    chunk_text: str
    section: Optional[str]
    char_start: int
    char_end: int
    chunk_index: int
    source: SourceRef


class SearchResponse(BaseModel):
    query: str
    company: str
    results: Optional[list[SearchHit]] = None
    weak_matches: Optional[list[SearchHit]] = None
    warning: Optional[str] = None
    suggestion: Optional[str] = None
    corpus: CorpusStats


class CompanyEntry(BaseModel):
    name: str
    article_count: int
    chunk_count: int
    last_ingested: Optional[str]


class CompaniesResponse(BaseModel):
    companies: list[CompanyEntry]


class ArticleRow(BaseModel):
    id: int
    url: str
    title: Optional[str]
    published_at: Optional[str]
    source_domain: Optional[str]
    status: str
    status_reason: Optional[str]
    chunk_count: int


class ArticlesResponse(BaseModel):
    company: str
    articles: list[ArticleRow]
