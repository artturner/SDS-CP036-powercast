import time
from fastapi.testclient import TestClient


def test_health_and_readiness_imports():
    # Import lazily to avoid side effects at collection time
    from app_core.main import app  # FastAPI instance
    client = TestClient(app)

    # Liveness should respond immediately
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data and "model_loaded" in data

    # Readiness may require model load; poll up to ~60s
    ready = False
    for _ in range(60):
        rr = client.get("/ready")
        if rr.status_code == 200:
            ready = True
            break
        time.sleep(1)
    assert ready, "Service did not become ready within 60s"

