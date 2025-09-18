"""
Test simulation and dummy data generation.
"""

import pytest
from datetime import datetime
from app_core.simulation import (
    generate_dummy_time_series,
    update_simulation_state,
    get_current_simulation_state,
    set_simulation_scenario
)


def test_generate_dummy_time_series():
    """Test dummy time series generation"""
    # Test default parameters
    data = generate_dummy_time_series()
    assert len(data) == 36  # Default timesteps
    assert len(data[0]) == 11  # Default features
    assert all(isinstance(row, list) for row in data)
    assert all(isinstance(val, float) for row in data for val in row)

    # Test custom parameters
    data = generate_dummy_time_series(timesteps=10, n_features=5, scenario="high_load")
    assert len(data) == 10
    assert len(data[0]) == 5


def test_scenario_variations():
    """Test different scenario types"""
    scenarios = ["normal", "high_load", "low_load", "peak_hours"]

    for scenario in scenarios:
        data = generate_dummy_time_series(scenario=scenario)
        assert len(data) == 36
        assert len(data[0]) == 11

        # Check that data values are reasonable
        temps = [row[0] for row in data]
        humidities = [row[1] for row in data]

        assert all(15 <= temp <= 35 for temp in temps)  # Reasonable temperature range
        assert all(20 <= humidity <= 90 for humidity in humidities)  # Reasonable humidity


def test_simulation_state_management():
    """Test simulation state updates"""
    # Get initial state
    initial_state = get_current_simulation_state()
    assert "current_time" in initial_state
    assert "scenario" in initial_state
    assert "simulation_running" in initial_state

    # Update state
    updated_state = update_simulation_state(advance_time=True)
    assert updated_state["current_time"] > initial_state["current_time"]


def test_set_simulation_scenario():
    """Test manual scenario setting"""
    # Test valid scenario
    state = set_simulation_scenario("high_load")
    assert state["scenario"] == "high_load"

    # Test invalid scenario
    with pytest.raises(ValueError):
        set_simulation_scenario("invalid_scenario")


def test_simulation_thread_safety():
    """Test that simulation operations are thread-safe"""
    import threading
    import time

    results = []

    def update_worker():
        for _ in range(5):
            state = update_simulation_state()
            results.append(state["current_time"])
            time.sleep(0.01)

    # Run multiple threads
    threads = [threading.Thread(target=update_worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Should have results from all threads
    assert len(results) == 15


def test_dummy_data_consistency():
    """Test that dummy data maintains consistency within scenarios"""
    # Generate data multiple times for same scenario
    data1 = generate_dummy_time_series(scenario="normal")
    data2 = generate_dummy_time_series(scenario="normal")

    # Should be identical (deterministic with fixed seed)
    assert data1 == data2

    # Different scenarios should produce different data
    high_load_data = generate_dummy_time_series(scenario="high_load")
    low_load_data = generate_dummy_time_series(scenario="low_load")

    # Calculate mean temperatures
    high_temp_mean = sum(row[0] for row in high_load_data) / len(high_load_data)
    low_temp_mean = sum(row[0] for row in low_load_data) / len(low_load_data)

    assert high_temp_mean > low_temp_mean  # High load should have higher temperature