# Contributing to Powercast API

Thank you for your interest in contributing to the Powercast API! This document provides guidelines and information for contributors.

## 🌟 Development Workflow

### Branch Strategy

We use a **Git Flow**-inspired branching strategy:

- **`main`**: Production-ready code. Protected branch.
- **`develop`**: Integration branch for features. Protected branch.
- **`feature/*`**: Feature development branches
- **`bugfix/*`**: Bug fix branches
- **`hotfix/*`**: Emergency production fixes

### Development Process

1. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Test thoroughly**:
   ```bash
   # Run all tests
   pytest tests/

   # Run with coverage
   pytest --cov=app_core tests/

   # Test Docker build
   docker build -t powercast-test .
   docker run -p 8000:8000 powercast-test
   ```

4. **Commit with clear messages**:
   ```bash
   git add .
   git commit -m "feat: add new prediction validation feature"
   ```

5. **Open a Pull Request** to `develop` (or `main` for hotfixes)

6. **Address review feedback** if needed

7. **Merge after approval** and CI checks pass

## 🔧 Setting Up Development Environment

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git

### Local Setup

```bash
# Clone the repository
git clone https://github.com/your-username/powercast-api.git
cd powercast-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run development server
uvicorn app_core.main:app --reload --port 8000
```

### Environment Variables for Development

```bash
# .env file for development
DEBUG=true
EVALUATE_ON_STARTUP=true
LOG_FORMAT=plain
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

## 📋 Code Standards

### Python Code Style

We follow **PEP 8** with some modifications:

- **Line length**: 127 characters (GitHub-friendly)
- **Imports**: Use absolute imports from `app_core`
- **Type hints**: Required for public functions
- **Docstrings**: Required for modules, classes, and public functions

### Code Formatting

We use **Black** for code formatting:

```bash
# Format code
black app_core tests/

# Check formatting
black --check app_core tests/
```

### Import Organization

```python
# Standard library imports
import os
import json
from typing import Dict, List, Optional

# Third-party imports
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local imports
from app_core.config import setup_logging
from app_core.schemas import PredictionRequest
```

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── test_health.py          # Health endpoint tests
├── test_predict_shape.py   # Prediction validation tests
├── test_inference_scaling.py  # Model inference tests
├── test_simulation.py      # Simulation logic tests
└── test_config.py          # Configuration tests
```

### Writing Tests

- **Unit tests**: Test individual functions/methods
- **Integration tests**: Test API endpoints
- **Mocking**: Mock external dependencies (model loading, file I/O)
- **Coverage**: Aim for >80% test coverage

### Test Example

```python
def test_prediction_validation():
    """Test that invalid inputs are properly rejected"""
    from app_core.main import app
    client = TestClient(app)

    # Test invalid temperature
    response = client.post("/predict", json={
        "features": [[100.0, 50.0] + [0.0] * 9] * 36,  # Invalid temp
        "normalize": True
    })
    assert response.status_code == 400
    assert "Temperature" in response.json()["detail"]
```

## 🔒 Security Guidelines

### Input Validation

- **Always validate** input data shape and ranges
- **Use Pydantic models** for request/response validation
- **Sanitize** user inputs before processing
- **Default to secure**: `echo_input=False` by default

### Environment Security

- **Never commit** secrets or API keys
- **Use environment variables** for configuration
- **Validate** environment variable values
- **Document** required vs optional variables

### API Security

- **Implement CORS** controls via `ALLOWED_ORIGINS`
- **Rate limiting** for production deployments
- **Input sanitization** for all endpoints
- **Error handling** without information leakage

## 🚀 Docker Guidelines

### Dockerfile Best Practices

- **Multi-stage builds** for optimization
- **Specific base images**: `python:3.10-slim`
- **Layer caching**: Copy requirements first
- **Security**: Run as non-root user
- **Health checks**: Include proper health endpoints

### Environment Variables

- **`PORT`**: Application port (required for cloud deployment)
- **`WORKERS`**: Gunicorn worker count
- **`EVALUATE_ON_STARTUP`**: Model validation flag
- **`LOG_FORMAT`**: Logging format (json/plain)

## 📖 Documentation Standards

### Code Documentation

```python
def make_prediction(features: np.ndarray, normalize: bool = True) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Make a prediction using the loaded model.

    Args:
        features: Input features array of shape (timesteps, features)
        normalize: Whether to apply feature scaling

    Returns:
        Tuple of (predictions, model_info)

    Raises:
        RuntimeError: If model is not loaded
        ValueError: If input shape is invalid
    """
```

### API Documentation

- **Use FastAPI automatic docs**: Available at `/docs`
- **Provide examples** in Pydantic models
- **Document response codes** and error conditions
- **Include usage examples** in README

## 🔍 Code Review Process

### For Authors

- **Self-review** your code before requesting review
- **Test thoroughly** including edge cases
- **Update documentation** for API changes
- **Keep PRs focused** on a single feature/fix
- **Write clear commit messages**

### For Reviewers

- **Check functionality**: Does it work as intended?
- **Review tests**: Are edge cases covered?
- **Security review**: Any security implications?
- **Performance**: Any performance impacts?
- **Documentation**: Is it clear and complete?

### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are comprehensive and pass
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced
- [ ] Performance is acceptable
- [ ] Breaking changes are documented

## 🚨 Issue Reporting

### Bug Reports

Include:
- **Environment**: OS, Python version, deployment method
- **Steps to reproduce**: Clear, numbered steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Logs**: Relevant error messages or logs

### Feature Requests

Include:
- **Use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives**: Other approaches considered
- **Implementation**: Any implementation ideas

## 📝 Commit Message Format

Use **conventional commits** format:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples

```bash
feat(api): add input validation for temperature ranges
fix(docker): correct healthcheck endpoint URL
docs(readme): update deployment instructions
test(inference): add tests for model prediction scaling
```

## 🎯 Performance Considerations

### Optimization Guidelines

- **Profile before optimizing**: Use proper profiling tools
- **Memory efficiency**: Avoid loading large datasets unnecessarily
- **Async where beneficial**: Use async for I/O operations
- **Caching**: Cache expensive computations when appropriate

### Monitoring

- **Health checks**: `/health` and `/ready` endpoints
- **Logging**: Structured logging for observability
- **Metrics**: Optional Prometheus metrics
- **Error tracking**: Comprehensive error handling

## 💡 Getting Help

- **Documentation**: Check README and API docs first
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Code Review**: Ask specific questions in PR comments

Thank you for contributing to Powercast API! 🚀