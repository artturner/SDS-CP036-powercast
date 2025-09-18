from fastapi.testclient import TestClient


def _get_dummy(client: TestClient):
    r = client.get("/dummy-data")
    assert r.status_code == 200
    return r.json()


def test_predict_accepts_correct_shape():
    from app_core.main import app
    client = TestClient(app)

    dummy = _get_dummy(client)
    features = dummy["data"]  # Updated field name
    r = client.post("/predict", json={"features": features, "normalize": True})
    assert r.status_code == 200
    data = r.json()
    assert "predictions" in data and len(data["predictions"]) == 3


def test_predict_rejects_bad_shape():
    from app_core.main import app
    client = TestClient(app)

    dummy = _get_dummy(client)
    features = dummy["data"]  # Updated field name
    # Remove one timestep to violate expected shape
    bad = features[:-1]
    r = client.post("/predict", json={"features": bad, "normalize": True})
    assert r.status_code == 400


def test_predict_input_validation():
    """Test enhanced input validation"""
    from app_core.main import app
    client = TestClient(app)

    # Test invalid temperature values
    dummy = _get_dummy(client)
    features = dummy["data"]

    # Invalid temperature (too high)
    bad_features = [row[:] for row in features]  # Deep copy
    bad_features[0][0] = 100.0  # Temperature too high
    r = client.post("/predict", json={"features": bad_features, "normalize": True})
    assert r.status_code == 400
    assert "Temperature" in r.json()["detail"]

    # Invalid humidity values
    bad_features = [row[:] for row in features]  # Deep copy
    bad_features[0][1] = 150.0  # Humidity > 100%
    r = client.post("/predict", json={"features": bad_features, "normalize": True})
    assert r.status_code == 400
    assert "Humidity" in r.json()["detail"]


def test_predict_echo_input_control():
    """Test input echo security control"""
    from app_core.main import app
    client = TestClient(app)

    dummy = _get_dummy(client)
    features = dummy["data"]

    # Test with echo_input=False (default)
    r = client.post("/predict", json={"features": features, "normalize": True})
    assert r.status_code == 200
    data = r.json()
    assert data.get("input_data") is None  # Should not echo input by default

    # Test with echo_input=True
    r = client.post("/predict", json={"features": features, "normalize": True, "echo_input": True})
    assert r.status_code == 200
    data = r.json()
    assert data.get("input_data") is not None  # Should echo input when requested

