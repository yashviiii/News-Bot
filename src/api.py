"""FastAPI application exposing /ingest, /search, /articles, /companies, /health."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, db as db_mod, models
from .ingest import pipeline
from .ingest.pipeline import _normalize_company
from .search import search as search_fn


config.configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Auto-create schema if DB is missing — keeps the 5-minute setup promise.
    if not Path(config.DB_PATH).exists():
        logger.info("Creating DB at %s on first start", config.DB_PATH)
        db_mod.init_db()
    yield


app = FastAPI(
    title="News Ingestion Pipeline",
    version="0.1.0",
    description=(
        "Local ingestion + hybrid search for company news. "
        "Open / for the UI."
    ),
    lifespan=lifespan,
)


_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    """Apply baseline security headers to every response.

    CSP is strict: only same-origin resources, inline script/style allowed for
    the single-file UI (no remote CDNs). Frame-ancestors blocks clickjacking;
    referrer policy strips the referer on outbound links.
    """
    response = await call_next(request)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers.setdefault("Content-Security-Policy", csp)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def _index() -> FileResponse:
    index_path = _STATIC_DIR / "index.html"
    if not index_path.is_file():
        return JSONResponse(  # type: ignore[return-value]
            status_code=404, content={"error": "UI not installed"}
        )
    return FileResponse(str(index_path), media_type="text/html; charset=utf-8")


@app.exception_handler(RequestValidationError)
async def _validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Reshape FastAPI's default 422 into the spec's 400 `{"error", "details"}` form.

    Errors are pre-encoded by FastAPI; we strip the `ctx` field which can hold
    objects that are not JSON-serializable across versions.
    """
    sanitized = []
    for err in exc.errors():
        sanitized.append(
            {
                "loc": list(err.get("loc", [])),
                "msg": str(err.get("msg", "")),
                "type": str(err.get("type", "")),
            }
        )
    return JSONResponse(
        status_code=400,
        content={"error": "request validation failed", "details": {"errors": sanitized}},
    )


@app.exception_handler(StarletteHTTPException)
async def _http_error_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Normalize HTTP errors into the spec's `{"error"}` shape."""
    detail = exc.detail if isinstance(exc.detail, str) else "request failed"
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.get("/health", response_model=models.HealthResponse)
def health() -> models.HealthResponse:
    return models.HealthResponse(status="ok", embedding_model=config.EMBED_MODEL_NAME)


@app.api_route("/ingest", methods=["GET", "POST"])
def ingest_endpoint(
    company: str = Query(..., min_length=1, max_length=200),
    force: bool = Query(False),
) -> JSONResponse:
    company = company.strip()
    if not company:
        return JSONResponse(
            status_code=400, content={"error": "company parameter required"}
        )
    try:
        summary = pipeline.run_ingest(company, force=force)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception:  # noqa: BLE001
        logger.exception("ingest failed")
        return JSONResponse(
            status_code=500, content={"error": "unexpected internal error"}
        )
    return JSONResponse(content=summary)


@app.get("/search")
def search_endpoint(
    q: str = Query(..., min_length=1, max_length=500),
    company: Optional[str] = Query(None, max_length=200),
    k: int = Query(config.DEFAULT_SEARCH_K, ge=1, le=config.MAX_SEARCH_K),
    threshold: float = Query(config.DEFAULT_THRESHOLD, ge=0.0, le=1.0),
    vector_only: bool = Query(False),
) -> JSONResponse:
    q = q.strip()
    company_clean = company.strip() if company else None
    if not q:
        return JSONResponse(
            status_code=400, content={"error": "query parameter required"}
        )
    try:
        out = search_fn(
            company_clean, q,
            k=k, threshold=threshold, vector_only=vector_only,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception:  # noqa: BLE001
        logger.exception("search failed")
        return JSONResponse(
            status_code=500, content={"error": "unexpected internal error"}
        )
    if "_not_found" in out:
        return JSONResponse(
            status_code=404,
            content={
                "error": (
                    f"No data ingested for '{out['_not_found']}'. "
                    f"Run POST /ingest?company={out['_not_found']} first."
                )
            },
        )
    if out.get("_infer_failed"):
        return JSONResponse(
            status_code=400,
            content={
                "error": out["message"],
                "details": {"query": out["query"]},
            },
        )
    return JSONResponse(content=out)


@app.get("/companies")
def companies_endpoint() -> JSONResponse:
    with db_mod.connect() as conn:
        rows = conn.execute(
            """
            SELECT c.name AS name,
                   COUNT(DISTINCT CASE WHEN a.status='ok' THEN a.id END) AS article_count,
                   COUNT(ch.id) AS chunk_count,
                   MAX(a.fetched_at) AS last_ingested
            FROM companies c
            LEFT JOIN articles a ON a.company_id = c.id
            LEFT JOIN chunks ch ON ch.article_id = a.id
            GROUP BY c.id, c.name
            ORDER BY last_ingested DESC NULLS LAST
            """
        ).fetchall()
    return JSONResponse(
        content={"companies": [dict(r) for r in rows]}
    )


@app.get("/articles")
def articles_endpoint(
    company: str = Query(..., min_length=1, max_length=200),
    status: Optional[str] = Query(None, max_length=32),
) -> JSONResponse:
    company = company.strip()
    if not company:
        return JSONResponse(
            status_code=400, content={"error": "company parameter required"}
        )
    norm = _normalize_company(company)
    with db_mod.connect() as conn:
        row = conn.execute(
            "SELECT id FROM companies WHERE normalized_name = ?", (norm,)
        ).fetchone()
        if row is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"No data ingested for '{company}'."},
            )
        company_id = int(row["id"])

        params: list = [company_id]
        sql = (
            "SELECT a.id AS id, a.url, a.title, a.published_at, a.source_domain, "
            "a.status, a.status_reason, "
            "(SELECT COUNT(*) FROM chunks WHERE chunks.article_id = a.id) AS chunk_count "
            "FROM articles a WHERE a.company_id = ?"
        )
        if status:
            sql += " AND a.status = ?"
            params.append(status)
        sql += " ORDER BY a.fetched_at DESC"
        rows = conn.execute(sql, params).fetchall()

    return JSONResponse(
        content={"company": company, "articles": [dict(r) for r in rows]}
    )
