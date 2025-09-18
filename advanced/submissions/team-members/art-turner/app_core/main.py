"""
Main FastAPI application using modularized structure.
"""

import logging
import time
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import (
    setup_logging, configure_cors, EVALUATE_ON_STARTUP
)
from .routes import api_router
from .inference import load_model_and_scalers, compute_validation_metrics
from .observability import setup_prometheus_metrics
from .simulation import update_simulation_state

# Setup logging first
logger = setup_logging(__name__)

# Create FastAPI application
app = FastAPI(
    title="Powercast API",
    description="Advanced Power Consumption Forecasting API using AttentionLSTM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global readiness state
ready = False


# Request timing middleware
@app.middleware("http")
async def add_timing_and_log(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000.0
    try:
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} in {duration_ms:.1f}ms")
    except Exception:
        pass
    response.headers["X-Process-Time-ms"] = f"{duration_ms:.1f}"
    return response


# Configure CORS
configure_cors(app)

# Mount static files if directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(api_router)

# Setup Prometheus metrics if enabled
enable_metrics = os.getenv("ENABLE_METRICS", "false").lower() == "true"
setup_prometheus_metrics(app, enable_metrics)


@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    global ready
    try:
        # Load model and scalers
        load_model_and_scalers()

        # Compute validation metrics only if enabled
        if EVALUATE_ON_STARTUP:
            logger.info("EVALUATE_ON_STARTUP enabled, computing validation metrics...")
            compute_validation_metrics()
        else:
            logger.info("EVALUATE_ON_STARTUP disabled, skipping validation metrics")

        # Initialize simulation state
        update_simulation_state(advance_time=False)

        ready = True
        update_ready_status(True)
        logger.info("Startup complete; readiness set to True")

    except Exception as e:
        ready = False
        update_ready_status(False)
        logger.error(f"Startup failed: {e}")
        raise


# Update ready status in observability module
def update_ready_status(status: bool):
    global ready
    ready = status
    from . import observability
    observability.ready = status