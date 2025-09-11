from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_hello_world():
    """Smoke test for hello world endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_check():
    """Smoke test for health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
