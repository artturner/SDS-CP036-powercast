import logging
import os
from typing import List

from fastapi.middleware.cors import CORSMiddleware


# Environment-driven flags
EVALUATE_ON_STARTUP = os.getenv("EVALUATE_ON_STARTUP", "false").lower() == "true"
USE_ONNX = os.getenv("USE_ONNX", "false").lower() == "true"
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_FORMAT = os.getenv("LOG_FORMAT", "plain").lower()

_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _origins_env.split(',') if o.strip()]


def setup_logging(name: str | None = None) -> logging.Logger:
    """Configure root logging and return a module logger.

    Respects LOG_FORMAT env: 'json' or 'plain'.
    """
    logger = logging.getLogger(name or __name__)
    root = logging.getLogger()
    level = logging.INFO
    root.setLevel(level)
    # Reset handlers for idempotent re-config
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)
    handler = logging.StreamHandler()
    if LOG_FORMAT == "json":
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
    else:
        fmt = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)
    return logger


def configure_cors(app) -> None:
    """Attach CORS middleware based on ALLOWED_ORIGINS."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

