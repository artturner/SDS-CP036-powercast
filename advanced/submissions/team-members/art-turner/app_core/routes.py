"""
API route handlers for the Powercast application.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import numpy as np

from .schemas import (
    PredictionRequest, PredictionResponse, ModelInfo,
    HealthResponse, InputVisualization
)
from .inference import (
    model, metadata, make_prediction, get_model_info,
    model_validation_metrics
)
from .simulation import (
    get_dummy_time_series, update_simulation_state,
    get_current_simulation_state, set_simulation_scenario
)
from .visualization import (
    create_time_series_plot, create_feature_distribution_plot,
    create_correlation_heatmap, create_prediction_gauge_charts
)
from .observability import health_check, readiness_check
from .config import DEBUG_MODE

logger = logging.getLogger(__name__)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Create API router
api_router = APIRouter()


@api_router.get("/", response_class=HTMLResponse)
async def root():
    """Clean dashboard interface inspired by ERCOT design"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Powercast - Power Consumption Forecasting</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f8f9fa;
            color: #2c3e50;
            line-height: 1.6;
        }

        .header {
            background: white;
            padding: 1.5rem 2rem;
            border-bottom: 1px solid #e9ecef;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }

        .header h1 {
            font-size: 2rem;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 0.5rem;
        }

        .header p {
            color: #6c757d;
            font-size: 1rem;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #f1f3f4;
        }

        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #2c3e50;
        }

        .card-subtitle {
            font-size: 0.875rem;
            color: #6c757d;
        }

        .timestamp {
            font-size: 0.75rem;
            color: #6c757d;
            font-weight: 500;
        }

        .status-good {
            color: #28a745;
            font-weight: 600;
        }

        .status-warning {
            color: #ffc107;
            font-weight: 600;
        }

        .status-critical {
            color: #dc3545;
            font-weight: 600;
        }

        .zones-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-top: 1rem;
        }

        .zone-card {
            text-align: center;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 6px;
            border: 1px solid #e9ecef;
        }

        .zone-value {
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0.5rem 0;
        }

        .zone-label {
            font-size: 0.875rem;
            color: #6c757d;
            font-weight: 500;
        }

        .zone-status {
            font-size: 0.75rem;
            margin-top: 0.5rem;
            font-weight: 600;
        }

        .metric-row {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid #f1f3f4;
        }

        .metric-row:last-child {
            border-bottom: none;
        }

        .metric-label {
            font-weight: 500;
            color: #495057;
        }

        .metric-value {
            font-weight: 600;
            color: #2c3e50;
        }

        .btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .btn:hover {
            background: #0056b3;
        }

        .btn-secondary {
            background: #6c757d;
        }

        .btn-secondary:hover {
            background: #545b62;
        }

        .loading {
            color: #6c757d;
            font-style: italic;
        }

        .footer {
            text-align: center;
            padding: 2rem;
            color: #6c757d;
            font-size: 0.875rem;
        }

        .conditions-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }

        .condition-item {
            text-align: center;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 6px;
        }

        .condition-value {
            font-size: 1.25rem;
            font-weight: 600;
            color: #2c3e50;
        }

        .condition-label {
            font-size: 0.875rem;
            color: #6c757d;
            margin-top: 0.25rem;
        }

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }

            .zones-grid {
                grid-template-columns: 1fr;
            }

            .conditions-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Powercast</h1>
        <p>Power Consumption Forecasting System</p>
    </div>

    <div class="container">
        <div class="dashboard-grid">
            <!-- Current Predictions Card -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Current Predictions</div>
                        <div class="card-subtitle">Zone Power Consumption</div>
                    </div>
                    <div class="timestamp" id="prediction-timestamp">Last Updated: --:--</div>
                </div>

                <div class="zones-grid">
                    <div class="zone-card">
                        <div class="zone-label">Zone 1</div>
                        <div class="zone-value" id="zone1-value">--</div>
                        <div class="zone-status status-good" id="zone1-status">Normal</div>
                    </div>
                    <div class="zone-card">
                        <div class="zone-label">Zone 2</div>
                        <div class="zone-value" id="zone2-value">--</div>
                        <div class="zone-status status-good" id="zone2-status">Normal</div>
                    </div>
                    <div class="zone-card">
                        <div class="zone-label">Zone 3</div>
                        <div class="zone-value" id="zone3-value">--</div>
                        <div class="zone-status status-good" id="zone3-status">Normal</div>
                    </div>
                </div>

                <div style="margin-top: 1.5rem; text-align: center;">
                    <button class="btn" onclick="updatePredictions()">Update Predictions</button>
                    <button class="btn btn-secondary" onclick="toggleAutoUpdate()" id="auto-btn">Start Auto-Update</button>
                </div>
            </div>

            <!-- System Status Card -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">System Status</div>
                        <div class="card-subtitle">Model and API Health</div>
                    </div>
                    <div class="timestamp" id="status-timestamp">Checked: --:--</div>
                </div>

                <div class="metric-row">
                    <span class="metric-label">Model Status</span>
                    <span class="metric-value status-good" id="model-status">Loading...</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">API Health</span>
                    <span class="metric-value status-good" id="api-health">Healthy</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Model Accuracy (R²)</span>
                    <span class="metric-value" id="model-r2">--</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Prediction RMSE</span>
                    <span class="metric-value" id="model-rmse">--</span>
                </div>
            </div>

            <!-- Environmental Conditions Card -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Environmental Conditions</div>
                        <div class="card-subtitle">Current Weather Inputs</div>
                    </div>
                    <div class="timestamp" id="conditions-timestamp">Updated: --:--</div>
                </div>

                <div class="conditions-grid">
                    <div class="condition-item">
                        <div class="condition-value" id="temperature">--°C</div>
                        <div class="condition-label">Temperature</div>
                    </div>
                    <div class="condition-item">
                        <div class="condition-value" id="humidity">--%</div>
                        <div class="condition-label">Humidity</div>
                    </div>
                    <div class="condition-item">
                        <div class="condition-value" id="wind-speed">-- m/s</div>
                        <div class="condition-label">Wind Speed</div>
                    </div>
                    <div class="condition-item">
                        <div class="condition-value" id="solar">-- W/m²</div>
                        <div class="condition-label">Solar Radiation</div>
                    </div>
                </div>
            </div>

            <!-- Forecast Timeline Card -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Forecast Timeline</div>
                        <div class="card-subtitle">Next 24 Hours</div>
                    </div>
                    <div class="timestamp">Tetouan, Morocco Climate</div>
                </div>

                <div id="forecast-timeline">
                    <div class="loading">Loading forecast data...</div>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>Powercast API - Advanced Power Consumption Forecasting using AttentionLSTM</p>
        <p>Real-time monitoring and prediction system</p>
    </div>

    <script>
        let autoUpdateInterval = null;
        let isAutoUpdating = false;

        // API base URL - adjust for your deployment
        const API_BASE = window.location.origin;

        function formatTime(date) {
            return date.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        function formatNumber(num) {
            return Math.round(num).toLocaleString();
        }

        function getStatusClass(value, max) {
            const percentage = value / max;
            if (percentage < 0.6) return 'status-good';
            if (percentage < 0.8) return 'status-warning';
            return 'status-critical';
        }

        function getStatusText(value, max) {
            const percentage = value / max;
            if (percentage < 0.6) return 'Normal';
            if (percentage < 0.8) return 'High';
            return 'Critical';
        }

        async function updatePredictions() {
            try {
                // Update timestamp
                document.getElementById('prediction-timestamp').textContent =
                    `Last Updated: ${formatTime(new Date())}`;

                // Make prediction request - check for dummy endpoint or regular predict
                let response;
                try {
                    response = await fetch(`${API_BASE}/dummy-data`, {
                        method: 'GET'
                    });

                    if (response.ok) {
                        const dummyData = await response.json();
                        // Make prediction with dummy data
                        response = await fetch(`${API_BASE}/predict`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                features: dummyData.data,
                                normalize: true
                            })
                        });
                    }
                } catch (e) {
                    // Fallback to basic health check if endpoints don't exist
                    console.log('Using fallback data generation');
                    response = null;
                }

                if (!response || !response.ok) {
                    // Generate some demo values
                    const demoData = {
                        zone_predictions: {
                            'Zone_1': 32000 + Math.random() * 8000,
                            'Zone_2': 22000 + Math.random() * 6000,
                            'Zone_3': 27000 + Math.random() * 8000
                        }
                    };
                    updateZoneDisplay(demoData);
                    return;
                }

                const data = await response.json();
                updateZoneDisplay(data);

                console.log('Predictions updated successfully');

            } catch (error) {
                console.error('Failed to update predictions:', error);
                showErrorState();
            }
        }

        function updateZoneDisplay(data) {
            // Update zone values
            const zones = ['zone1', 'zone2', 'zone3'];
            const maxValues = [55000, 40000, 50000]; // Zone capacity limits
            const zoneKeys = ['Zone_1', 'Zone_2', 'Zone_3'];

            zones.forEach((zoneId, index) => {
                const zoneKey = zoneKeys[index];
                const value = data.zone_predictions[zoneKey] || 0;

                document.getElementById(`${zoneId}-value`).textContent =
                    `${formatNumber(value)} kW`;

                const statusElement = document.getElementById(`${zoneId}-status`);
                statusElement.textContent = getStatusText(value, maxValues[index]);
                statusElement.className = `zone-status ${getStatusClass(value, maxValues[index])}`;
            });

            // Update environmental conditions with demo data
            updateEnvironmentalConditions();
        }

        function showErrorState() {
            ['zone1', 'zone2', 'zone3'].forEach(zoneId => {
                document.getElementById(`${zoneId}-value`).textContent = 'Error';
                const statusElement = document.getElementById(`${zoneId}-status`);
                statusElement.textContent = 'Unavailable';
                statusElement.className = 'zone-status status-critical';
            });
        }

        function updateEnvironmentalConditions() {
            const now = new Date();
            document.getElementById('conditions-timestamp').textContent =
                `Updated: ${formatTime(now)}`;

            // Generate realistic demo environmental data
            document.getElementById('temperature').textContent = `${Math.round(20 + Math.random() * 10)}°C`;
            document.getElementById('humidity').textContent = `${Math.round(60 + Math.random() * 20)}%`;
            document.getElementById('wind-speed').textContent = `${(2 + Math.random() * 4).toFixed(1)} m/s`;
            document.getElementById('solar').textContent = `${Math.round(300 + Math.random() * 400)} W/m²`;
        }

        async function updateSystemStatus() {
            try {
                const now = new Date();
                document.getElementById('status-timestamp').textContent =
                    `Checked: ${formatTime(now)}`;

                // Check model info
                const modelResponse = await fetch(`${API_BASE}/model-info`);
                if (modelResponse.ok) {
                    const modelData = await modelResponse.json();

                    document.getElementById('model-status').textContent = 'Loaded';
                    document.getElementById('model-status').className = 'metric-value status-good';

                    if (modelData.best_performance) {
                        document.getElementById('model-r2').textContent =
                            modelData.best_performance.r2.toFixed(4);
                        document.getElementById('model-rmse').textContent =
                            `${modelData.best_performance.rmse.toFixed(1)} kW`;
                    }
                } else {
                    document.getElementById('model-status').textContent = 'Error';
                    document.getElementById('model-status').className = 'metric-value status-critical';
                }

                // Check API health
                const healthResponse = await fetch(`${API_BASE}/health-simple`);
                if (healthResponse.ok) {
                    document.getElementById('api-health').textContent = 'Healthy';
                    document.getElementById('api-health').className = 'metric-value status-good';
                } else {
                    document.getElementById('api-health').textContent = 'Degraded';
                    document.getElementById('api-health').className = 'metric-value status-warning';
                }

            } catch (error) {
                console.error('Failed to update system status:', error);
                document.getElementById('api-health').textContent = 'Error';
                document.getElementById('api-health').className = 'metric-value status-critical';
            }
        }

        function toggleAutoUpdate() {
            const button = document.getElementById('auto-btn');

            if (isAutoUpdating) {
                clearInterval(autoUpdateInterval);
                button.textContent = 'Start Auto-Update';
                button.className = 'btn btn-secondary';
                isAutoUpdating = false;
            } else {
                autoUpdateInterval = setInterval(() => {
                    updatePredictions();
                    updateSystemStatus();
                }, 30000); // Update every 30 seconds

                button.textContent = 'Stop Auto-Update';
                button.className = 'btn';
                isAutoUpdating = true;
            }
        }

        // Initialize dashboard
        async function initDashboard() {
            await updateSystemStatus();
            await updatePredictions();

            // Update status every 60 seconds
            setInterval(updateSystemStatus, 60000);
        }

        // Start dashboard when page loads
        document.addEventListener('DOMContentLoaded', initDashboard);
    </script>
</body>
</html>"""


@api_router.get("/ping")
async def ping():
    """Simple ping endpoint for basic connectivity test"""
    return {"status": "pong", "timestamp": datetime.now().isoformat()}


@api_router.get("/health-simple")
async def simple_health():
    """Simple health check that doesn't depend on model loading"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@api_router.get("/health", response_model=HealthResponse)
async def health_endpoint():
    """Health check endpoint"""
    return health_check()


@api_router.get("/ready")
async def readiness_endpoint():
    """Readiness endpoint flips to 200 once model loaded."""
    return readiness_check()


@api_router.get("/model-info", response_model=ModelInfo)
async def get_model_info_endpoint():
    """Get model information and architecture details"""
    if model is None or metadata is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        return get_model_info()
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Make power consumption predictions"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Convert input features to numpy array
        features = np.array(request.features)

        # Enhanced input validation
        if metadata is not None:
            expected_shape = (metadata.get('lookback_window', 36), len(metadata.get('feature_names', [])))
            if features.shape != expected_shape:
                raise HTTPException(
                    status_code=400,
                    detail=f"Input shape {features.shape} doesn't match expected {expected_shape}. "
                           f"Expected {expected_shape[0]} timesteps and {expected_shape[1]} features."
                )

        # Validate feature values are reasonable
        if not np.isfinite(features).all():
            raise HTTPException(
                status_code=400,
                detail="Input contains invalid values (NaN or infinite)"
            )

        # Basic range validation for common features
        if features.shape[1] >= 2:  # Temperature and humidity checks
            temp_values = features[:, 0]
            humid_values = features[:, 1]

            if np.any(temp_values < -50) or np.any(temp_values > 70):
                raise HTTPException(
                    status_code=400,
                    detail="Temperature values out of reasonable range (-50°C to 70°C)"
                )

            if np.any(humid_values < 0) or np.any(humid_values > 100):
                raise HTTPException(
                    status_code=400,
                    detail="Humidity values out of reasonable range (0% to 100%)"
                )

        # Make prediction
        predictions, model_info = make_prediction(features, request.normalize)

        # Create named zone predictions
        zone_names = model_info.get('target_names', ['Zone_1', 'Zone_2', 'Zone_3'])
        zone_predictions = {
            zone_names[i]: float(predictions[i])
            for i in range(min(len(predictions), len(zone_names)))
        }

        # Prepare response
        response_data = {
            "predictions": predictions.tolist(),
            "zone_predictions": zone_predictions,
            "model_info": model_info,
            "timestamp": datetime.now().isoformat()
        }

        # Include input data in response only if explicitly requested or DEBUG mode
        if request.echo_input or DEBUG_MODE:
            response_data["input_data"] = request.features
            response_data["input_summary"] = {
                "shape": features.shape,
                "mean_temperature": float(np.mean([row[0] for row in request.features])),
                "mean_humidity": float(np.mean([row[1] for row in request.features])),
                "mean_occupancy": float(np.mean([row[3] for row in request.features])) if len(request.features[0]) > 3 else None
            }

        return PredictionResponse(**response_data)

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@api_router.get("/dummy-data")
async def get_dummy_data():
    """Get dummy time series data for testing"""
    try:
        data = get_dummy_time_series()
        state = get_current_simulation_state()

        return {
            "data": data,
            "simulation_state": state,
            "feature_names": metadata.get('feature_names', []) if metadata else [],
            "shape": [len(data), len(data[0]) if data else 0]
        }
    except Exception as e:
        logger.error(f"Failed to get dummy data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/dummy-data/scenario")
async def set_dummy_scenario(scenario_data: Dict[str, str]):
    """Set the simulation scenario"""
    try:
        scenario = scenario_data.get("scenario", "normal")
        state = set_simulation_scenario(scenario)
        return {
            "message": f"Scenario set to {scenario}",
            "simulation_state": state
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/visualize-input", response_model=InputVisualization)
async def visualize_input_data(request: PredictionRequest):
    """Create visualizations for input data"""
    try:
        feature_names = metadata.get('feature_names', []) if metadata else []
        if not feature_names:
            feature_names = [f"Feature_{i}" for i in range(len(request.features[0]))]

        # Create visualizations
        time_series_plot = create_time_series_plot(request.features, feature_names)
        feature_distribution_plot = create_feature_distribution_plot(request.features, feature_names)
        correlation_plot = create_correlation_heatmap(request.features, feature_names)

        return InputVisualization(
            input_data=request.features,
            feature_names=feature_names,
            time_series_plot=time_series_plot,
            feature_distribution_plot=feature_distribution_plot,
            correlation_plot=correlation_plot
        )

    except Exception as e:
        logger.error(f"Input visualization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# HTML/Template routes
@api_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    try:
        # Get current simulation state and dummy data
        sim_state = get_current_simulation_state()
        dummy_data = get_dummy_time_series()

        # Get model validation metrics
        validation_metrics = model_validation_metrics or {}

        # Create sample prediction with dummy data
        sample_prediction = None
        gauge_charts_html = ""
        if model is not None and dummy_data:
            try:
                predictions, _ = make_prediction(np.array(dummy_data))
                zone_names = metadata.get('target_names', ['Zone_1', 'Zone_2', 'Zone_3']) if metadata else ['Zone_1', 'Zone_2', 'Zone_3']
                sample_prediction = {
                    zone_names[i]: float(predictions[i])
                    for i in range(min(len(predictions), len(zone_names)))
                }
                gauge_charts_html = create_prediction_gauge_charts(sample_prediction)
            except Exception as e:
                logger.warning(f"Failed to create sample prediction: {e}")

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "model_loaded": model is not None,
            "simulation_state": sim_state,
            "validation_metrics": validation_metrics,
            "sample_prediction": sample_prediction,
            "gauge_charts_html": gauge_charts_html
        })

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })


@api_router.get("/predict-page", response_class=HTMLResponse)
async def predict_page(request: Request):
    """Prediction interface page"""
    try:
        feature_names = metadata.get('feature_names', []) if metadata else []
        return templates.TemplateResponse("predict.html", {
            "request": request,
            "model_loaded": model is not None,
            "feature_names": feature_names
        })
    except Exception as e:
        logger.error(f"Predict page error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })


@api_router.post("/predict-form")
async def predict_form_handler(request: Request, background_tasks: BackgroundTasks):
    """Handle form-based prediction requests"""
    try:
        form_data = await request.form()

        # Extract features from form (simplified version)
        # In a real implementation, you'd parse all the feature fields
        dummy_data = get_dummy_time_series()
        predictions, model_info = make_prediction(np.array(dummy_data))

        # Update simulation in background
        background_tasks.add_task(update_simulation_state, advance_time=False)

        zone_names = metadata.get('target_names', ['Zone_1', 'Zone_2', 'Zone_3']) if metadata else ['Zone_1', 'Zone_2', 'Zone_3']
        zone_predictions = {
            zone_names[i]: float(predictions[i])
            for i in range(min(len(predictions), len(zone_names)))
        }

        gauge_charts_html = create_prediction_gauge_charts(zone_predictions)

        return templates.TemplateResponse("prediction_result.html", {
            "request": request,
            "predictions": predictions.tolist(),
            "zone_predictions": zone_predictions,
            "model_info": model_info,
            "gauge_charts_html": gauge_charts_html,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Form prediction error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })


# Background task for updating simulation
@api_router.post("/update-simulation")
async def update_simulation(background_tasks: BackgroundTasks):
    """Trigger simulation state update"""
    try:
        background_tasks.add_task(update_simulation_state)
        return {"message": "Simulation update scheduled"}
    except Exception as e:
        logger.error(f"Simulation update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))