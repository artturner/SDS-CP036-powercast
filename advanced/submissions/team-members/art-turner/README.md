# ⚡ Powercast API - Advanced Power Consumption Forecasting

A production-ready FastAPI deployment featuring an **AttentionLSTM** model for multi-zone power consumption forecasting.

## 🚀 Features

- **High-Performance Model**: AttentionLSTM achieving R² = 0.9941
- **RESTful API**: FastAPI with automatic documentation and enhanced security
- **Advanced UI**: Interactive dashboard with real-time visualizations
- **Docker Support**: Optimized containerized deployment with hardening
- **Cloud Ready**: Configured for Railway.app and Render.com deployment
- **Real-time Predictions**: WebSocket-like real-time prediction updates
- **Comprehensive Testing**: Built-in API testing and validation
- **Modular Architecture**: Clean separation of concerns with app_core modules
- **Environment Controls**: Feature flags for startup behavior and security
- **Enhanced Observability**: Health checks, readiness endpoints, and structured logging

## 📊 Model Performance

- **Architecture**: AttentionLSTM (256 hidden, 2 layers, 0.2 dropout)
- **Best R²**: 0.9941
- **RMSE**: 343.4 kW
- **MAE**: 242.9 kW
- **Input**: 36 timesteps × 11 features (environmental + cyclical)
- **Output**: 3 zones power consumption predictions

## 🔧 Local Development

### Prerequisites
- Python 3.10+
- pip

### Installation
```bash
# Clone and navigate to the project
cd powercast-deployment

# Install dependencies
pip install -r requirements.txt

# Start the development server
uvicorn app_core.main:app --reload --port 8000
```

### Access the Application
- **API Documentation**: http://localhost:8000/docs
- **Advanced Dashboard**: http://localhost:8000/dashboard
- **Simple UI**: http://localhost:8000/
- **Health Check**: http://localhost:8000/health
- **Readiness Check**: http://localhost:8000/ready

## 🐳 Docker Deployment

### Build and Run
```bash
# Build Docker image
docker build -t powercast-api .

# Run container (bind to PORT)
docker run -e PORT=8080 -p 8080:8080 powercast-api

# Or using docker-compose
docker-compose up --build
```

## ☁️ Railway Deployment (Docker)

Deploy using the Dockerfile to ensure correct $PORT binding and health checks.

- Set service to deploy from Dockerfile
- Configure Environment Variables:
  - `WORKERS=1` (or 2 for larger plans)
  - `ALLOWED_ORIGINS=https://your-frontend.app,http://localhost:3000`
  - `EVALUATE_ON_STARTUP=false` (recommended on small instances)
  - `LOG_FORMAT=plain` (or `json`)

Health paths:
- Liveness: `/health`
- Readiness: `/ready`

Logs show gunicorn bound to `$PORT` automatically.

## ☁️ Render.com Deployment

### Deploy to Render.com

1. **Connect Repository**:
   - Connect your GitHub repository to Render.com
   - Select "Web Service" deployment type

2. **Configuration**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app_core.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
   - **Environment**: Python 3.10

3. **Environment Variables** (Optional):
   - `PYTHON_VERSION`: 3.10.12
   - `PORT`: 8000 (automatically set by Render)

4. **Health Check Path**: `/health` (optionally use `/ready` for readiness)

### Alternative: YAML Configuration
Use the included `render.yaml` for infrastructure-as-code deployment:
```bash
render deploy
```

## ⚙️ Environment Configuration

The application supports several environment variables for production optimization:

### Core Environment Variables

- **`PORT`**: Port to bind to (default: 8000, auto-set by cloud providers)
- **`WORKERS`**: Number of Gunicorn workers (default: 2)
- **`ALLOWED_ORIGINS`**: CORS origins, comma-separated (default: localhost)

### Feature Flags

- **`EVALUATE_ON_STARTUP`**: Compute validation metrics on startup (default: false)
  - Set to `true` for detailed model metrics, `false` for faster cold starts
- **`USE_ONNX`**: Use ONNX runtime instead of PyTorch (default: false)
  - Future optimization for smaller memory footprint
- **`DEBUG`**: Enable debug features like input echoing (default: false)
- **`LOG_FORMAT`**: Logging format - `json` or `plain` (default: plain)
- **`ENABLE_METRICS`**: Enable Prometheus metrics endpoint (default: false)

### Production Recommendations

For Railway/Render deployment:
```bash
WORKERS=1                    # Start with 1 worker on small instances
EVALUATE_ON_STARTUP=false    # Skip validation for faster startup
ALLOWED_ORIGINS=https://your-domain.com
LOG_FORMAT=json             # Structured logging for production
```

For development:
```bash
DEBUG=true                   # Enable input echoing and verbose logging
EVALUATE_ON_STARTUP=true     # Show model performance metrics
LOG_FORMAT=plain            # Human-readable logs
```

## 📡 API Endpoints

### Core Prediction Endpoints

- `POST /predict` - Custom feature prediction with enhanced validation
- `POST /visualize-input` - Generate visualizations for input data
- `GET /dummy-data` - Generate sample input data for testing
- `POST /dummy-data/scenario` - Set simulation scenario

### Information Endpoints

- `GET /health` - Service health status
- `GET /ready` - Service readiness status (model loaded)
- `GET /model-info` - Model architecture and performance metrics
- `GET /` - Basic web UI
- `GET /dashboard` - Advanced interactive dashboard

### API Request Example

```python
import requests

# Custom prediction with enhanced security controls
response = requests.post("https://your-app.onrender.com/predict", json={
    "features": [[25.5, 60.2, 3.1, 0.8, 0.6, 0.5, 0.87, -0.71, 0.71, 0.0, 1.0]] * 36,
    "normalize": True,
    "echo_input": False  # Security: don't echo input data back
})

prediction = response.json()
print(f"Zone 1: {prediction['zone_predictions']['Zone 1']:.2f} kW")
print(f"Zone 2: {prediction['zone_predictions']['Zone 2']:.2f} kW") 
print(f"Zone 3: {prediction['zone_predictions']['Zone 3']:.2f} kW")
```

### JavaScript/Browser Example

```javascript
// Quick demo prediction
fetch('/predict-demo', { method: 'POST' })
  .then(response => response.json())
  .then(data => {
    console.log('Predictions:', data.zone_predictions);
    console.log('Total Power:', 
      data.predictions[0] + data.predictions[1] + data.predictions[2]
    );
  });
```

## 📊 Features Overview

### Input Features (11 total)
1. **Environmental** (5 features):
   - Temperature (°C)
   - Humidity (%)
   - Wind Speed (m/s) 
   - General Diffuse Flows (W/m²)
   - Diffuse Flows (W/m²)

2. **Cyclical Time** (6 features):
   - Hour sin/cos (24h cycle)
   - Day of week sin/cos (weekly cycle)
   - Month sin/cos (seasonal cycle)

### Output Predictions
- Zone 1 Power Consumption (kW)
- Zone 2 Power Consumption (kW) 
- Zone 3 Power Consumption (kW)

## 🎯 Advanced Dashboard Features

- **Real-time Predictions**: Live prediction generation
- **Interactive Charts**: Dynamic time series visualization using Chart.js
- **Model Metrics**: Performance statistics display
- **Custom Input**: JSON input validation and testing
- **Prediction History**: Track and analyze recent predictions
- **Batch Processing**: Generate multiple predictions
- **Export Ready**: Copy-paste predictions for external analysis

## 🔒 Production Considerations

- **Model Security**: Models loaded securely without external dependencies
- **Scalability**: Gunicorn multi-worker deployment
- **Monitoring**: Health checks and logging
- **Error Handling**: Comprehensive error responses
- **Input Validation**: Pydantic models for request validation
- **CORS**: Controlled via `ALLOWED_ORIGINS` env (comma-separated)
- **Feature Flags**:
  - `EVALUATE_ON_STARTUP` (default: false) – compute validation metrics on boot
  - `USE_ONNX` (default: false) – reserve for ONNX runtime path (future)
  - `LOG_FORMAT` (plain|json) – structured logs
  - `WORKERS` – gunicorn worker count

## 🧪 Testing

The application includes comprehensive test coverage:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run specific test files
pytest tests/test_health.py
pytest tests/test_predict_shape.py
pytest tests/test_inference_scaling.py

# Run with coverage
pytest --cov=app_core tests/
```

### Test Coverage
- **Health & Readiness**: Service availability and model loading
- **Prediction Validation**: Input shape and value validation
- **Security Controls**: Input echo controls and validation
- **Inference Logic**: Model prediction and scaling
- **Configuration**: Environment variable handling
- **Simulation**: Dummy data generation and scenarios

## 🏗️ Architecture

The application uses a modular architecture for maintainability:

```
app_core/
├── main.py           # FastAPI application and startup
├── config.py         # Environment configuration and logging
├── routes.py         # API route handlers
├── schemas.py        # Pydantic models and validation
├── inference.py      # Model loading and prediction logic
├── simulation.py     # Dummy data generation and state management
├── visualization.py  # Chart and plot generation
└── observability.py  # Health checks and monitoring
```

### Key Design Principles
- **Separation of Concerns**: Each module has a single responsibility
- **Environment-Driven**: All behavior controllable via environment variables
- **Security by Default**: Input echoing disabled, CORS restricted, validation enforced
- **Observability**: Comprehensive logging, health checks, and metrics
- **Testing**: Full test coverage with mocked dependencies

## 🛠️ Development Commands

```bash
# Run development server with auto-reload
uvicorn app_core.main:app --reload --host 0.0.0.0 --port 8000

# Test API endpoints
curl -X GET "http://localhost:8000/dummy-data"
curl -X GET "http://localhost:8000/health"

# View API documentation
open http://localhost:8000/docs

# Check health
curl http://localhost:8000/health

## ✅ Testing

Install dev dependencies and run tests locally:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest -q
```
```

## 📁 Project Structure

```
powercast-deployment/
├── app.py                          # FastAPI application
├── advanced_models.py              # Model architectures
├── week2_feature_engineering_fixed.py  # Data preprocessing
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker configuration
├── render.yaml                     # Render.com deployment config
├── templates/
│   └── dashboard.html             # Advanced UI template
├── static/                        # Static assets (if needed)
├── *.pkl                         # Model scalers
├── *.json                        # Dataset metadata
└── README.md                     # This file
```

## 🚀 Live Demo

Once deployed to Render.com, your API will be available at:
- `https://your-app-name.onrender.com/dashboard` - Interactive Dashboard
- `https://your-app-name.onrender.com/docs` - API Documentation

## 📈 Performance Notes

- **Cold Start**: ~10-15 seconds (free tier)
- **Response Time**: <200ms for predictions
- **Memory Usage**: ~512MB
- **Model Size**: ~2MB (PyTorch state dict)

## 🔍 Troubleshooting

### Common Issues
1. **ImportError**: Ensure all dependencies in requirements.txt
2. **Model Loading**: Check file paths for .pkl and .json files
3. **Memory Limits**: Consider reducing model size for free tier
4. **Timeout**: Increase gunicorn timeout for slower predictions

### Logs
Check Render.com deployment logs for detailed error information.

---

Built with ❤️ using FastAPI, PyTorch, and Chart.js for the **Advanced Power Consumption Forecasting Challenge**.
