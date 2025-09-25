"""
API route handlers for the Powercast application.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import numpy as np
import httpx

from .schemas import (
    PredictionRequest, PredictionResponse, ModelInfo,
    HealthResponse, InputVisualization
)
from . import inference
from .simulation import (
    get_dummy_time_series, update_simulation_state,
    get_current_simulation_state, set_simulation_scenario,
    generate_7day_consumption_forecast
)
from .visualization import (
    create_time_series_plot, create_feature_distribution_plot,
    create_correlation_heatmap, create_prediction_gauge_charts
)
from .observability import health_check, readiness_check
from .config import DEBUG_MODE, METEOSOURCE_API_KEY

logger = logging.getLogger(__name__)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Create API router
api_router = APIRouter()

# Simple in-memory cache for weather data (respects rate limits)
weather_cache: Optional[Dict] = None
weather_cache_timestamp: Optional[datetime] = None
WEATHER_CACHE_DURATION = timedelta(hours=1)  # Cache for 1 hour to respect rate limits


@api_router.get("/", response_class=HTMLResponse)
async def root():
    """Clean dashboard interface inspired by ERCOT design"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Powercast - Power Consumption Forecasting</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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

        .forecast-day {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid #f1f3f4;
        }

        .forecast-day:last-child {
            border-bottom: none;
        }

        .forecast-date {
            flex: 1;
            font-weight: 500;
            font-size: 0.875rem;
            color: #495057;
        }

        .forecast-weather {
            flex: 2;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .weather-icon {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            font-size: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .weather-icon.sunny { background: #f39c12; color: white; }
        .weather-icon.cloudy { background: #95a5a6; color: white; }
        .weather-icon.rainy { background: #3498db; color: white; }

        .weather-desc {
            font-size: 0.8rem;
            color: #6c757d;
        }

        .forecast-temp {
            flex: 1;
            text-align: right;
            font-weight: 600;
            color: #2c3e50;
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
            <!-- 7-Day Consumption Forecast Card -->
            <div class="card" style="grid-column: span 2;">
                <div class="card-header">
                    <div>
                        <div class="card-title">7-Day Power Consumption Forecast</div>
                        <div class="card-subtitle">Weather-Driven Predictions by Zone</div>
                    </div>
                    <div class="timestamp" id="forecast-timestamp">Last Updated: --:--</div>
                </div>

                <div id="consumption-chart" style="height: 400px; margin: 1rem 0; position: relative;">
                    <canvas id="forecastChart"></canvas>
                    <div id="chart-loading" class="loading" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">Loading 7-day forecast...</div>
                </div>

                <div style="margin-top: 1rem; text-align: center;">
                    <button class="btn" onclick="update7DayForecast()">Update Forecast</button>
                    <button class="btn btn-secondary" onclick="toggleAutoUpdate()" id="auto-btn">Start Auto-Update</button>
                </div>

                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #f1f3f4; font-size: 0.75rem; color: #6c757d;">
                    <div>Forecast combines real weather data with AI predictions</div>
                    <div>Model Accuracy: R² = 0.8234, RMSE = 2.85 MW (95% confidence bands)</div>
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


            <!-- Forecast Timeline Card -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">7-Day Weather Forecast</div>
                        <div class="card-subtitle">Tetouan, Morocco</div>
                    </div>
                    <div class="timestamp">Live Weather Data</div>
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

        // Global chart instance
        let forecastChart = null;

        async function update7DayForecast() {
            try {
                // Update timestamp
                document.getElementById('forecast-timestamp').textContent =
                    `Last Updated: ${formatTime(new Date())}`;

                // Show loading
                document.getElementById('chart-loading').style.display = 'block';

                // Fetch 7-day consumption forecast
                const response = await fetch(`${API_BASE}/7day-consumption-forecast`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                displayForecastChart(data.consumption_forecast);

                console.log('7-day forecast updated successfully');

            } catch (error) {
                console.error('Failed to update 7-day forecast:', error);
                showForecastError();
            } finally {
                document.getElementById('chart-loading').style.display = 'none';
            }
        }

        function displayForecastChart(forecastData) {
            const ctx = document.getElementById('forecastChart').getContext('2d');

            // Prepare data for Chart.js (convert kW to MW)
            const labels = forecastData.dates.map(date => {
                const d = new Date(date);
                return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            });

            const zone1Data = forecastData.zone1_consumption.map(kw => kw / 1000);
            const zone2Data = forecastData.zone2_consumption.map(kw => kw / 1000);
            const zone3Data = forecastData.zone3_consumption.map(kw => kw / 1000);
            const confidenceUpper = forecastData.confidence_upper.map(kw => kw / 1000);
            const confidenceLower = forecastData.confidence_lower.map(kw => kw / 1000);

            // Destroy existing chart
            if (forecastChart) {
                forecastChart.destroy();
            }

            // Create new chart
            forecastChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Zone 1',
                            data: zone1Data,
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            fill: false,
                            tension: 0.4
                        },
                        {
                            label: 'Zone 2',
                            data: zone2Data,
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            fill: false,
                            tension: 0.4
                        },
                        {
                            label: 'Zone 3',
                            data: zone3Data,
                            borderColor: '#ffc107',
                            backgroundColor: 'rgba(255, 193, 7, 0.1)',
                            fill: false,
                            tension: 0.4
                        },
                        {
                            label: 'Upper Confidence (95%)',
                            data: confidenceUpper,
                            borderColor: '#dc3545',
                            backgroundColor: 'rgba(220, 53, 69, 0.05)',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            fill: '+1',
                            pointRadius: 0
                        },
                        {
                            label: 'Lower Confidence (95%)',
                            data: confidenceLower,
                            borderColor: '#dc3545',
                            backgroundColor: 'rgba(220, 53, 69, 0.05)',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            fill: false,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: '7-Day Power Consumption Forecast (Weather-Driven)',
                            font: {
                                size: 16,
                                weight: 'bold'
                            }
                        },
                        legend: {
                            position: 'top',
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.dataset.label}: ${context.parsed.y.toFixed(1)} MW`;
                                },
                                footer: function(tooltipItems) {
                                    if (tooltipItems[0] && forecastData.weather_info) {
                                        const weatherInfo = forecastData.weather_info[tooltipItems[0].dataIndex];
                                        return `Weather: ${weatherInfo.temperature}°C, ${weatherInfo.wind_speed} m/s wind, ${weatherInfo.cloud_cover}% clouds`;
                                    }
                                    return '';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Power Consumption (MW)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return value.toFixed(1) + ' MW';
                                }
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        }
                    }
                }
            });
        }

        function showForecastError() {
            const ctx = document.getElementById('forecastChart').getContext('2d');
            if (forecastChart) {
                forecastChart.destroy();
            }

            // Show error message
            document.getElementById('consumption-chart').innerHTML =
                '<div class="loading" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">Failed to load forecast data</div>';
        }


        async function updateForecast() {
            try {
                const response = await fetch(`${API_BASE}/weather-forecast`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                displayForecast(data);

            } catch (error) {
                console.error('Failed to update forecast:', error);
                document.getElementById('forecast-timeline').innerHTML =
                    '<div class="loading">Failed to load forecast data</div>';
            }
        }

        function displayForecast(data) {
            const forecastContainer = document.getElementById('forecast-timeline');
            const forecast = data.forecast || data;

            if (!forecast || forecast.length === 0) {
                forecastContainer.innerHTML = '<div class="loading">No forecast data available</div>';
                return;
            }

            let html = '';
            forecast.forEach(day => {
                const date = new Date(day.date);
                const formattedDate = date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric'
                });

                const weatherClass = getWeatherIconClass(day.weather);
                const weatherIcon = getWeatherIcon(day.weather);

                html += `
                    <div class="forecast-day">
                        <div class="forecast-date">${formattedDate}</div>
                        <div class="forecast-weather">
                            <div class="weather-icon ${weatherClass}">${weatherIcon}</div>
                            <div class="weather-desc">${capitalizeWords(day.weather.replace(/_/g, ' '))}</div>
                        </div>
                        <div class="forecast-temp">${Math.round(day.temperature.max)}°/${Math.round(day.temperature.min)}°</div>
                    </div>
                `;
            });

            // Add attribution at the bottom
            html += `
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #f1f3f4; text-align: center;">
                    <a href="https://www.meteosource.com" target="_blank"
                       style="font-size: 0.75rem; color: #6c757d; text-decoration: none;">
                        Powered by Meteosource
                    </a>
                    ${data.cached ? ' <span style="font-size: 0.7rem; color: #28a745;">• Cached</span>' : ''}
                </div>
            `;

            forecastContainer.innerHTML = html;
        }

        function getWeatherIconClass(weather) {
            if (weather.includes('sunny') || weather.includes('clear')) return 'sunny';
            if (weather.includes('rain') || weather.includes('shower')) return 'rainy';
            return 'cloudy';
        }

        function getWeatherIcon(weather) {
            if (weather.includes('sunny') || weather.includes('clear')) return '☀';
            if (weather.includes('rain') || weather.includes('shower')) return '🌧';
            if (weather.includes('cloud')) return '☁';
            return '☀';
        }

        function capitalizeWords(str) {
            return str.split(' ').map(word =>
                word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' ');
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
                    update7DayForecast();
                    updateSystemStatus();
                    updateForecast();
                    // Weather updates less frequently to respect API limits
                }, 30000); // Update every 30 seconds

                button.textContent = 'Stop Auto-Update';
                button.className = 'btn';
                isAutoUpdating = true;
            }
        }

        // Initialize dashboard
        async function initDashboard() {
            await updateSystemStatus();
            await update7DayForecast();
            await updateForecast();

            // Update status every 60 seconds
            setInterval(updateSystemStatus, 60000);
            // Update 7-day forecast every hour
            setInterval(update7DayForecast, 3600000);
            // Update weather forecast every 2 hours to respect API limits (1 hour cache + buffer)
            setInterval(updateForecast, 7200000);
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
    if inference.model is None or inference.metadata is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        return inference.get_model_info()
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Make power consumption predictions"""
    if inference.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Convert input features to numpy array
        features = np.array(request.features)

        # Enhanced input validation
        if inference.metadata is not None:
            expected_shape = (inference.metadata.get('lookback_window', 36), len(inference.metadata.get('base_feature_cols', [])))
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
        predictions, model_info = inference.make_prediction(features, request.normalize)

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
            "feature_names": inference.metadata.get('base_feature_cols', []) if inference.metadata else [],
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
        feature_names = inference.metadata.get('base_feature_cols', []) if inference.metadata else []
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


@api_router.get("/weather-forecast")
async def get_weather_forecast():
    """Get 7-day weather forecast for Tetouan, Morocco with caching to respect API limits"""
    global weather_cache, weather_cache_timestamp

    try:
        # Check if we have valid cached data
        now = datetime.now()
        if (weather_cache is not None and
            weather_cache_timestamp is not None and
            now - weather_cache_timestamp < WEATHER_CACHE_DURATION):
            logger.info("Returning cached weather data to respect API rate limits")
            return weather_cache

        # Fetch fresh data from API
        logger.info("Fetching fresh weather data from Meteosource API")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://www.meteosource.com/api/v1/free/point",
                params={
                    "place_id": "tetouan",
                    "sections": "daily",
                    "language": "en",
                    "units": "auto",
                    "key": METEOSOURCE_API_KEY
                },
                headers={"accept": "application/json"}
            )

            if response.status_code != 200:
                # If API fails but we have cached data, return it
                if weather_cache is not None:
                    logger.warning(f"API error {response.status_code}, returning cached data")
                    return weather_cache
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Weather API error: {response.text}"
                )

            weather_data = response.json()

            # Process and clean the data for frontend consumption
            forecast_data = {
                "location": "Tetouan, Morocco",
                "timezone": weather_data.get("timezone", "Africa/Casablanca"),
                "forecast": [],
                "cached": False,
                "attribution": "Powered by Meteosource",
                "attribution_url": "https://www.meteosource.com"
            }

            for day_data in weather_data.get("daily", {}).get("data", []):
                all_day = day_data.get("all_day", {})
                forecast_data["forecast"].append({
                    "date": day_data.get("day"),
                    "weather": day_data.get("weather"),
                    "icon": day_data.get("icon"),
                    "summary": day_data.get("summary"),
                    "temperature": {
                        "avg": all_day.get("temperature"),
                        "min": all_day.get("temperature_min"),
                        "max": all_day.get("temperature_max")
                    },
                    "wind": all_day.get("wind", {}),
                    "cloud_cover": all_day.get("cloud_cover", {}).get("total", 0),
                    "precipitation": all_day.get("precipitation", {}).get("total", 0)
                })

            # Cache the result
            weather_cache = forecast_data.copy()
            weather_cache["cached"] = True
            weather_cache_timestamp = now

            return forecast_data

    except httpx.TimeoutException:
        # Return cached data if available during timeout
        if weather_cache is not None:
            logger.warning("API timeout, returning cached weather data")
            return weather_cache
        raise HTTPException(status_code=504, detail="Weather service timeout")
    except Exception as e:
        logger.error(f"Weather forecast error: {e}")
        # Return cached data if available during error
        if weather_cache is not None:
            logger.warning("API error, returning cached weather data")
            return weather_cache
        raise HTTPException(status_code=500, detail="Failed to fetch weather forecast")


@api_router.get("/7day-consumption-forecast")
async def get_7day_consumption_forecast():
    """Get 7-day power consumption forecast driven by real weather data"""
    try:
        # First get the weather forecast
        weather_response = await get_weather_forecast()

        if "forecast" not in weather_response:
            raise HTTPException(status_code=503, detail="Weather data not available")

        # Generate consumption forecast using weather data
        consumption_forecast = generate_7day_consumption_forecast(weather_response["forecast"])

        if "error" in consumption_forecast:
            raise HTTPException(status_code=500, detail=consumption_forecast["error"])

        # Combine weather and consumption data
        result = {
            "location": weather_response.get("location", "Tetouan, Morocco"),
            "timezone": weather_response.get("timezone", "Africa/Casablanca"),
            "forecast_type": "7-day consumption forecast driven by weather",
            "model_accuracy": {
                "rmse": 2847.5,
                "r2": 0.8234,
                "confidence_level": "95%"
            },
            "consumption_forecast": consumption_forecast,
            "weather_attribution": weather_response.get("attribution", "Powered by Meteosource"),
            "attribution_url": weather_response.get("attribution_url", "https://www.meteosource.com"),
            "cached_weather": weather_response.get("cached", False),
            "generated_at": datetime.now().isoformat()
        }

        return result

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"7-day consumption forecast error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate consumption forecast")


# HTML/Template routes
@api_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    try:
        # Get current simulation state and dummy data
        sim_state = get_current_simulation_state()
        dummy_data = get_dummy_time_series()

        # Get model validation metrics
        validation_metrics = inference.model_validation_metrics or {}

        # Create sample prediction with dummy data
        sample_prediction = None
        gauge_charts_html = ""
        if inference.model is not None and dummy_data:
            try:
                predictions, _ = inference.make_prediction(np.array(dummy_data))
                zone_names = inference.metadata.get('target_names', ['Zone_1', 'Zone_2', 'Zone_3']) if inference.metadata else ['Zone_1', 'Zone_2', 'Zone_3']
                sample_prediction = {
                    zone_names[i]: float(predictions[i])
                    for i in range(min(len(predictions), len(zone_names)))
                }
                gauge_charts_html = create_prediction_gauge_charts(sample_prediction)
            except Exception as e:
                logger.warning(f"Failed to create sample prediction: {e}")

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "model_loaded": inference.model is not None,
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
        feature_names = inference.metadata.get('base_feature_cols', []) if inference.metadata else []
        return templates.TemplateResponse("predict.html", {
            "request": request,
            "model_loaded": inference.model is not None,
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
        predictions, model_info = inference.make_prediction(np.array(dummy_data))

        # Update simulation in background
        background_tasks.add_task(update_simulation_state, advance_time=False)

        zone_names = inference.metadata.get('target_names', ['Zone_1', 'Zone_2', 'Zone_3']) if inference.metadata else ['Zone_1', 'Zone_2', 'Zone_3']
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