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
    """Root endpoint for Railway compatibility"""
    return """
    <html>
        <head>
            <title>Powercast API</title>
        </head>
        <body>
            <h1>Powercast API</h1>
            <p>Power Consumption Forecasting API using AttentionLSTM</p>
            <p>Status: <a href="/health">Health Check</a> | <a href="/ready">Readiness</a> | <a href="/docs">API Docs</a></p>
        </body>
    </html>
    """


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