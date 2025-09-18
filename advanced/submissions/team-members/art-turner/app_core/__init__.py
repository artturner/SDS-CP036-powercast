"""
Powercast application core modules.
"""

from .config import (
    EVALUATE_ON_STARTUP,
    USE_ONNX,
    DEBUG_MODE,
    LOG_FORMAT,
    ALLOWED_ORIGINS,
    setup_logging,
    configure_cors
)

from .schemas import (
    PredictionRequest,
    PredictionResponse,
    ModelInfo,
    HealthResponse,
    InputVisualization
)

from .inference import (
    load_model_and_scalers,
    compute_validation_metrics,
    make_prediction,
    get_model_info
)

from .routes import api_router

from .observability import setup_prometheus_metrics

__all__ = [
    'EVALUATE_ON_STARTUP',
    'USE_ONNX',
    'DEBUG_MODE',
    'LOG_FORMAT',
    'ALLOWED_ORIGINS',
    'setup_logging',
    'configure_cors',
    'PredictionRequest',
    'PredictionResponse',
    'ModelInfo',
    'HealthResponse',
    'InputVisualization',
    'load_model_and_scalers',
    'compute_validation_metrics',
    'make_prediction',
    'get_model_info',
    'api_router',
    'setup_prometheus_metrics'
]

