"""
Test configuration and environment handling.
"""

import os
import pytest
from unittest.mock import patch


def test_environment_flag_parsing():
    """Test environment variable parsing"""
    from app_core.config import EVALUATE_ON_STARTUP, USE_ONNX, DEBUG_MODE

    # Test with default values (should be False)
    assert EVALUATE_ON_STARTUP is False
    assert USE_ONNX is False
    assert DEBUG_MODE is False


def test_allowed_origins_parsing():
    """Test CORS origins parsing"""
    with patch.dict(os.environ, {'ALLOWED_ORIGINS': 'http://localhost:3000,https://example.com,http://test.local'}):
        # Reimport to get updated environment
        import importlib
        from app_core import config
        importlib.reload(config)

        expected = ['http://localhost:3000', 'https://example.com', 'http://test.local']
        assert config.ALLOWED_ORIGINS == expected


def test_log_format_configuration():
    """Test logging format configuration"""
    from app_core.config import setup_logging

    # Test plain format (default)
    logger = setup_logging("test")
    assert logger is not None

    # Test JSON format
    with patch.dict(os.environ, {'LOG_FORMAT': 'json'}):
        import importlib
        from app_core import config
        importlib.reload(config)

        logger_json = config.setup_logging("test_json")
        assert logger_json is not None


def test_cors_configuration():
    """Test CORS middleware configuration"""
    from fastapi import FastAPI
    from app_core.config import configure_cors

    app = FastAPI()
    configure_cors(app)

    # Should add CORS middleware without error
    assert len(app.user_middleware) > 0


def test_environment_overrides():
    """Test environment variable overrides"""
    test_env = {
        'EVALUATE_ON_STARTUP': 'true',
        'USE_ONNX': 'true',
        'DEBUG': 'true',
        'LOG_FORMAT': 'json',
        'ALLOWED_ORIGINS': 'https://production.example.com'
    }

    with patch.dict(os.environ, test_env):
        # Reimport to get updated environment
        import importlib
        from app_core import config
        importlib.reload(config)

        assert config.EVALUATE_ON_STARTUP is True
        assert config.USE_ONNX is True
        assert config.DEBUG_MODE is True
        assert config.LOG_FORMAT == 'json'
        assert config.ALLOWED_ORIGINS == ['https://production.example.com']


def test_invalid_boolean_parsing():
    """Test invalid boolean value parsing defaults to False"""
    with patch.dict(os.environ, {'EVALUATE_ON_STARTUP': 'invalid', 'USE_ONNX': 'maybe'}):
        import importlib
        from app_core import config
        importlib.reload(config)

        # Invalid values should default to False
        assert config.EVALUATE_ON_STARTUP is False
        assert config.USE_ONNX is False