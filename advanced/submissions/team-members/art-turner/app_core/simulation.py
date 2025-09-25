"""
Dummy data simulation and state management for testing and demonstrations.
Now enhanced with real weather data integration for realistic forecasting.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Global simulation state
dummy_time_series = []
simulation_state = {
    "current_time": datetime.now(),
    "last_update": datetime.now(),
    "scenario": "normal",
    "anomaly_active": False,
    "simulation_running": True
}
simulation_lock = threading.Lock()


def generate_dummy_time_series(
    timesteps: int = 36,
    n_features: int = 11,
    scenario: str = "normal"
) -> List[List[float]]:
    """Generate dummy time series data for testing.

    Args:
        timesteps: Number of time steps
        n_features: Number of features
        scenario: Scenario type ('normal', 'high_load', 'low_load', 'peak_hours')

    Returns:
        List of feature vectors for each timestep
    """
    np.random.seed(42)  # For reproducible dummy data

    # Base patterns for different scenarios
    if scenario == "high_load":
        temp_base = 28.0
        humidity_base = 65.0
        occupancy_base = 0.9
    elif scenario == "low_load":
        temp_base = 20.0
        humidity_base = 45.0
        occupancy_base = 0.3
    elif scenario == "peak_hours":
        temp_base = 25.0
        humidity_base = 55.0
        occupancy_base = 0.8
    else:  # normal
        temp_base = 23.0
        humidity_base = 50.0
        occupancy_base = 0.6

    time_series = []

    for t in range(timesteps):
        # Generate realistic patterns with some noise
        progress = t / timesteps

        # Temperature with daily cycle
        temperature = temp_base + 3 * np.sin(2 * np.pi * progress) + np.random.normal(0, 1)

        # Humidity (inverse relationship with temperature)
        humidity = humidity_base - 10 * np.sin(2 * np.pi * progress) + np.random.normal(0, 3)
        humidity = max(30, min(80, humidity))  # Clamp between reasonable values

        # Wind speed
        wind_speed = 2.0 + np.random.exponential(1.5)

        # Occupancy patterns
        occupancy = max(0, min(1, occupancy_base + 0.2 * np.sin(4 * np.pi * progress) + np.random.normal(0, 0.1)))

        # Energy efficiency factors
        hvac_efficiency = 0.6 + 0.3 * np.random.random()
        lighting_efficiency = 0.5 + 0.4 * np.random.random()

        # Seasonal and time-based features
        seasonal_factor = 0.8 + 0.4 * np.sin(2 * np.pi * progress / 365 * 30)  # Monthly variation
        time_factor_sin = np.sin(2 * np.pi * progress)
        time_factor_cos = np.cos(2 * np.pi * progress)

        # Day of week (0-6, encoded as binary)
        day_of_week = int(progress * 7) % 7
        is_weekend = float(day_of_week >= 5)  # Fri-Sat weekend
        is_weekday = 1.0 - is_weekend

        # Combine into feature vector matching training data format
        features = [
            float(temperature),          # Temperature
            float(humidity),             # Humidity
            float(wind_speed),           # Wind Speed
            float(occupancy),            # Occupancy
            float(hvac_efficiency),      # HVAC Efficiency
            float(lighting_efficiency),  # Lighting Efficiency
            float(seasonal_factor),      # Seasonal Factor
            float(time_factor_sin),      # Time Factor (sin)
            float(time_factor_cos),      # Time Factor (cos)
            float(is_weekend),           # Is Weekend
            float(is_weekday)            # Is Weekday
        ]

        time_series.append(features)

    return time_series


def generate_weather_driven_time_series(
    weather_forecast: List[Dict],
    timesteps_per_day: int = 24,
    start_date: Optional[datetime] = None
) -> List[List[float]]:
    """Generate realistic time series data using real weather forecast.

    Args:
        weather_forecast: List of daily weather data from Meteosource API
        timesteps_per_day: Number of timesteps per day (24 for hourly)
        start_date: Starting date for the forecast

    Returns:
        List of feature vectors matching model requirements (14 features)
    """
    if not weather_forecast:
        # Fallback to dummy data if no weather available
        return generate_dummy_time_series()

    if start_date is None:
        start_date = datetime.now()

    time_series = []

    # Model expects 36 timesteps, so generate data for multiple days
    days_needed = min(len(weather_forecast), 7)  # Use up to 7 days

    for day_idx in range(days_needed):
        weather_day = weather_forecast[day_idx]
        current_date = start_date + timedelta(days=day_idx)

        # Extract weather data
        temp_min = weather_day['temperature']['min']
        temp_max = weather_day['temperature']['max']
        temp_avg = weather_day['temperature']['avg']
        wind_speed = weather_day['wind']['speed']
        cloud_cover = weather_day['cloud_cover']  # 0-100%
        precipitation = weather_day['precipitation']

        # Calculate solar radiation from cloud cover (inverse relationship)
        solar_radiation = (100 - cloud_cover) / 100.0  # 0-1 scale

        # Estimate humidity from temperature and precipitation
        # Higher temp = lower humidity, rain = higher humidity
        humidity = max(30, min(90, 70 - (temp_avg - 20) * 2 + precipitation * 10))

        for hour in range(timesteps_per_day):
            if len(time_series) >= 36:  # Model expects exactly 36 timesteps
                break

            # Create realistic hourly variations
            hour_progress = hour / 24.0

            # Temperature variation throughout the day (sinusoidal)
            temp_variation = (temp_max - temp_min) / 2 * np.sin(2 * np.pi * (hour_progress - 0.25))
            temperature = temp_avg + temp_variation

            # Adjust wind speed with some variation
            wind_variation = wind_speed + np.random.normal(0, wind_speed * 0.2)
            wind_variation = max(0, wind_variation)

            # Solar varies by time of day (peak at noon)
            if 6 <= hour <= 18:  # Daylight hours
                solar_hour_factor = np.sin(np.pi * (hour - 6) / 12)
                general_diffuse = solar_radiation * solar_hour_factor * 800  # W/m²
                diffuse_flows = general_diffuse * 0.7  # Diffuse component
            else:
                general_diffuse = 0
                diffuse_flows = 0

            # Time encodings
            hour_sin = np.sin(2 * np.pi * hour / 24)
            hour_cos = np.cos(2 * np.pi * hour / 24)

            # Day of week encodings
            dow = current_date.weekday()
            dow_sin = np.sin(2 * np.pi * dow / 7)
            dow_cos = np.cos(2 * np.pi * dow / 7)

            # Month encodings
            month = current_date.month
            month_sin = np.sin(2 * np.pi * month / 12)
            month_cos = np.cos(2 * np.pi * month / 12)

            # Placeholder consumption (will be replaced with chained predictions)
            zone1_consumption = 30000 + np.random.normal(0, 2000)
            zone2_consumption = 25000 + np.random.normal(0, 1500)
            zone3_consumption = 28000 + np.random.normal(0, 1800)

            # Create feature vector matching model expectations (14 features)
            features = [
                float(temperature),          # 0: Temperature
                float(humidity),             # 1: Humidity
                float(wind_variation),       # 2: Wind Speed
                float(general_diffuse),      # 3: general diffuse flows
                float(diffuse_flows),        # 4: diffuse flows
                float(hour_sin),             # 5: hour_sin
                float(hour_cos),             # 6: hour_cos
                float(dow_sin),              # 7: dow_sin
                float(dow_cos),              # 8: dow_cos
                float(month_sin),            # 9: month_sin
                float(month_cos),            # 10: month_cos
                float(zone1_consumption),    # 11: Zone 1 Power Consumption
                float(zone2_consumption),    # 12: Zone 2 Power Consumption
                float(zone3_consumption)     # 13: Zone 3 Power Consumption
            ]

            time_series.append(features)

        if len(time_series) >= 36:
            break

    # Pad if needed to reach 36 timesteps
    while len(time_series) < 36:
        # Repeat the last timestep with some variation
        if time_series:
            last_features = time_series[-1].copy()
            # Add small variations
            for i in range(3):  # Temperature, Humidity, Wind
                last_features[i] += np.random.normal(0, last_features[i] * 0.05)
            time_series.append(last_features)
        else:
            # Fallback to dummy data
            return generate_dummy_time_series()

    return time_series[:36]  # Ensure exactly 36 timesteps


def update_simulation_state(advance_time: bool = True) -> Dict[str, Any]:
    """Update the global simulation state and generate new dummy data.

    Args:
        advance_time: Whether to advance the simulation time

    Returns:
        Updated simulation state
    """
    global dummy_time_series, simulation_state

    with simulation_lock:
        if advance_time:
            # Advance simulation time
            time_increment = timedelta(minutes=15)  # 15-minute intervals
            simulation_state["current_time"] += time_increment
            simulation_state["last_update"] = datetime.now()

        # Determine scenario based on time
        current_hour = simulation_state["current_time"].hour
        current_day = simulation_state["current_time"].weekday()

        if current_day >= 5:  # Weekend
            if 10 <= current_hour <= 16:
                scenario = "normal"
            else:
                scenario = "low_load"
        else:  # Weekday
            if 8 <= current_hour <= 10 or 17 <= current_hour <= 19:
                scenario = "peak_hours"
            elif 6 <= current_hour <= 22:
                scenario = "normal"
            else:
                scenario = "low_load"

        # Add occasional anomalies
        if np.random.random() < 0.05:  # 5% chance of anomaly
            scenario = "high_load"
            simulation_state["anomaly_active"] = True
        else:
            simulation_state["anomaly_active"] = False

        simulation_state["scenario"] = scenario

        # Generate new dummy time series
        dummy_time_series = generate_dummy_time_series(scenario=scenario)

        logger.info(f"Simulation updated: scenario={scenario}, time={simulation_state['current_time']}")

        return simulation_state.copy()


def get_current_simulation_state() -> Dict[str, Any]:
    """Get the current simulation state without updating it."""
    with simulation_lock:
        return simulation_state.copy()


def get_dummy_time_series() -> List[List[float]]:
    """Get the current dummy time series data."""
    global dummy_time_series
    with simulation_lock:
        if not dummy_time_series:
            dummy_time_series = generate_dummy_time_series()
        return dummy_time_series.copy()


def set_simulation_scenario(scenario: str) -> Dict[str, Any]:
    """Manually set the simulation scenario.

    Args:
        scenario: One of 'normal', 'high_load', 'low_load', 'peak_hours'

    Returns:
        Updated simulation state
    """
    global dummy_time_series, simulation_state

    valid_scenarios = ["normal", "high_load", "low_load", "peak_hours"]
    if scenario not in valid_scenarios:
        raise ValueError(f"Invalid scenario. Must be one of: {valid_scenarios}")

    with simulation_lock:
        simulation_state["scenario"] = scenario
        simulation_state["last_update"] = datetime.now()

        # Generate new data for the scenario
        dummy_time_series = generate_dummy_time_series(scenario=scenario)

        logger.info(f"Simulation scenario manually set to: {scenario}")

        return simulation_state.copy()


def generate_7day_consumption_forecast(weather_forecast: List[Dict], model_inference_func=None) -> Dict[str, Any]:
    """Generate a realistic 7-day power consumption forecast using weather data.

    Each day's prediction builds on the previous day with variance within model accuracy.

    Args:
        weather_forecast: List of daily weather data from Meteosource API
        model_inference_func: Function to make model predictions

    Returns:
        Dictionary containing 7-day forecast with dates, consumption, and confidence bands
    """
    if not weather_forecast:
        return {"error": "No weather forecast data available"}

    forecast_days = min(len(weather_forecast), 7)
    results = {
        "dates": [],
        "zone1_consumption": [],
        "zone2_consumption": [],
        "zone3_consumption": [],
        "confidence_upper": [],
        "confidence_lower": [],
        "weather_info": []
    }

    # Model accuracy for confidence bands (from model metadata)
    model_rmse = 2847.5  # kW
    confidence_multiplier = 1.96  # 95% confidence interval

    # Base consumption levels (typical daily averages)
    base_consumption = {
        "zone1": 32000,  # kW
        "zone2": 24000,  # kW
        "zone3": 28000   # kW
    }

    # Previous day consumption (starting point)
    prev_consumption = base_consumption.copy()

    start_date = datetime.now().date()

    for day_idx in range(forecast_days):
        weather_day = weather_forecast[day_idx]
        forecast_date = start_date + timedelta(days=day_idx)

        # Extract key weather factors that affect consumption
        temp_avg = weather_day['temperature']['avg']
        wind_speed = weather_day['wind']['speed']
        cloud_cover = weather_day['cloud_cover']

        # Weather impact factors
        # Hot/cold weather increases consumption (HVAC)
        temp_impact = abs(temp_avg - 22) * 0.02  # 2% per degree from comfort zone

        # High wind can reduce heating needs
        wind_impact = -wind_speed * 0.01  # 1% reduction per m/s

        # Cloudy weather increases lighting needs
        cloud_impact = cloud_cover * 0.001  # 0.1% per % cloud cover

        # Combined weather impact (capped at ±20%)
        weather_factor = max(0.8, min(1.2, 1 + temp_impact + wind_impact + cloud_impact))

        # Day-to-day variation within model accuracy
        daily_variation = {
            "zone1": np.random.normal(0, model_rmse * 0.7),
            "zone2": np.random.normal(0, model_rmse * 0.6),
            "zone3": np.random.normal(0, model_rmse * 0.8)
        }

        # Calculate consumption: previous day + weather influence + daily variation
        zone1_forecast = prev_consumption["zone1"] * weather_factor + daily_variation["zone1"]
        zone2_forecast = prev_consumption["zone2"] * weather_factor + daily_variation["zone2"]
        zone3_forecast = prev_consumption["zone3"] * weather_factor + daily_variation["zone3"]

        # Ensure reasonable bounds (minimum 10kW, maximum 60kW per zone)
        zone1_forecast = max(10000, min(60000, zone1_forecast))
        zone2_forecast = max(10000, min(50000, zone2_forecast))
        zone3_forecast = max(10000, min(55000, zone3_forecast))

        # Confidence bands based on model RMSE
        total_forecast = zone1_forecast + zone2_forecast + zone3_forecast
        confidence_band = confidence_multiplier * model_rmse

        # Store results
        results["dates"].append(forecast_date.strftime("%Y-%m-%d"))
        results["zone1_consumption"].append(round(zone1_forecast, 1))
        results["zone2_consumption"].append(round(zone2_forecast, 1))
        results["zone3_consumption"].append(round(zone3_forecast, 1))
        results["confidence_upper"].append(round(total_forecast + confidence_band, 1))
        results["confidence_lower"].append(round(total_forecast - confidence_band, 1))
        results["weather_info"].append({
            "temperature": temp_avg,
            "wind_speed": wind_speed,
            "cloud_cover": cloud_cover,
            "weather": weather_day.get("weather", "unknown")
        })

        # Update previous consumption for next iteration (with momentum)
        momentum = 0.3  # How much previous day influences next day
        prev_consumption["zone1"] = prev_consumption["zone1"] * momentum + zone1_forecast * (1 - momentum)
        prev_consumption["zone2"] = prev_consumption["zone2"] * momentum + zone2_forecast * (1 - momentum)
        prev_consumption["zone3"] = prev_consumption["zone3"] * momentum + zone3_forecast * (1 - momentum)

    return results


# Initialize simulation on module import
dummy_time_series = generate_dummy_time_series()