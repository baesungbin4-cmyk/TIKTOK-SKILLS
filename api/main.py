from __future__ import annotations

import logging
import sys
import time
import uuid
from datetime import date
from typing import Any, Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from agent.planner import AgentResponse, TikTokAgent

try:
    from prometheus_fastapi_instrumentator import Instrumentator, metrics
except ImportError:  # pragma: no cover - exercised only in incomplete local envs
    Instrumentator = None
    metrics = None

# ============================================================
# Structured JSON logging
# ============================================================

def setup_logging() -> logging.Logger:
    """Configure structured JSON logging for production log aggregation."""
    try:
        from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    except ImportError:
        # Fallback to standard logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    return logging.getLogger("api")

logger = setup_logging()

# ============================================================
# Application
# ============================================================

app = FastAPI(title="TikTok Data Analysis Agent", version="0.1.0")
agent = TikTokAgent()
metrics_enabled = Instrumentator is not None and metrics is not None

# ============================================================
# Prometheus metrics
# ============================================================
if metrics_enabled:
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/healthz", "/metrics"],
    )
    instrumentator.add(
        metrics.latency(buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0))
    )
    instrumentator.add(metrics.request_size())
    instrumentator.add(metrics.response_size())
    instrumentator.instrument(app).expose(app, include_in_schema=False)
else:
    logger.warning(
        "metrics_disabled",
        extra={"reason": "prometheus_fastapi_instrumentator is not installed"},
    )


# ============================================================
# Request ID middleware
# ============================================================

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
    start = time.monotonic()

    # Log incoming request
    logger.info(
        "request_start",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown",
        },
    )

    response = await call_next(request)

    elapsed = time.monotonic() - start
    response.headers["X-Request-ID"] = request_id

    # Log completed request
    logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "status": response.status_code,
            "elapsed_ms": round(elapsed * 1000, 2),
        },
    )
    return response


# ============================================================
# Models
# ============================================================

class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=1)
    target_type: Literal["video", "account", "hashtag", "user"] = "hashtag"
    target_id: str = "demo"
    date_range: tuple[date, date] | None = None
    limit: int = Field(default=50, ge=1, le=200)


# ============================================================
# Routes
# ============================================================

@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "tiktok-data-analysis-agent",
        "data_source": "mock",
        "is_live_tiktok_api_configured": False,
        "metrics_enabled": metrics_enabled,
    }


@app.get("/skills")
async def skills() -> dict[str, Any]:
    return {"skills": agent.tool_schemas()}


@app.post("/analyze", response_model=AgentResponse)
async def analyze(request: AnalyzeRequest) -> AgentResponse:
    logger.info(
        "analyze_request",
        extra={
            "query": request.query,
            "target_type": request.target_type,
            "target_id": request.target_id,
        },
    )
    return await agent.run(
        request.query,
        target_type=request.target_type,
        target_id=request.target_id,
        date_range=request.date_range,
        limit=request.limit,
    )
