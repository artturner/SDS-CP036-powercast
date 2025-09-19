"""
Observability module for health checks, monitoring, and metrics.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException

from .schemas import HealthResponse
from . import inference

# Global ready state - will be set by main.py
ready = False

logger = logging.getLogger(__name__)


def health_check() -> HealthResponse:
    """Health check endpoint logic."""
    return HealthResponse(
        status="healthy" if inference.model is not None else "unhealthy",
        model_loaded=inference.model is not None,
        timestamp=datetime.now().isoformat()
    )


def readiness_check() -> Dict[str, Any]:
    """Readiness endpoint logic - returns 200 if ready, 503 if not."""
    if ready and inference.model is not None:
        return {
            "status": "ready",
            "model_loaded": True,
            "timestamp": datetime.now().isoformat()
        }
    raise HTTPException(
        status_code=503,
        detail={"status": "starting", "model_loaded": False}
    )


def setup_prometheus_metrics(app, enable_metrics: bool = False):
    """Setup Prometheus metrics if enabled.

    Args:
        app: FastAPI application instance
        enable_metrics: Whether to enable metrics collection
    """
    if not enable_metrics:
        return

    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        instrumentator = Instrumentator()
        instrumentator.instrument(app).expose(app)
        logger.info("Prometheus metrics enabled at /metrics")

    except ImportError:
        logger.warning("prometheus-fastapi-instrumentator not installed, skipping metrics")
    except Exception as e:
        logger.error(f"Failed to setup Prometheus metrics: {e}")


def log_request_info(method: str, path: str, status_code: int, duration_ms: float):
    """Log request information in structured format."""
    logger.info(
        f"{method} {path} -> {status_code} in {duration_ms:.1f}ms",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms
        }
    )