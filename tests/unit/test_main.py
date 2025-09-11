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


def test_router_integration():
    """Test that router endpoints are properly loaded and accessible."""
    # Test /api/obs/status endpoint exists (should return 500 without proper setup, but endpoint exists)
    response = client.get("/api/obs/status")
    # Should not be 404 (endpoint exists), but may be 500 due to missing dependencies
    assert response.status_code != 404

    # Test /api/obs/sync endpoint exists
    response = client.post("/api/obs/sync")
    assert response.status_code != 404

    # Test search endpoint exists
    response = client.post("/api/obs/search", json={"query": "test"})
    assert response.status_code != 404


def test_router_status_endpoint_exists():
    """Test that status endpoint exists and is accessible (integration test)."""
    response = client.get("/api/obs/status")
    assert response.status_code == 200
    response_data = response.json()

    # Verify response structure (actual response from real coordinator)
    assert "sync_status" in response_data
    assert "repository" in response_data
    assert "vector_store" in response_data
