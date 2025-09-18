"""
Dummy data simulation and state management for testing and demonstrations.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
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


# Initialize simulation on module import
dummy_time_series = generate_dummy_time_series()