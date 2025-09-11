import os

import httpx
import pytest


@pytest.fixture(scope="module")
def api_base_url():
    """
    Provides the base URL for the API service.
    Uses the conftest.py e2e_setup fixture for container management.
    """
    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8005")
    return f"http://{host_bind_ip}:{host_port}"


def test_e2e_hello_world(api_base_url: str):
    """End-to-end smoke test for hello world endpoint."""
    with httpx.Client(base_url=api_base_url) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}


def test_e2e_health_check(api_base_url: str):
    """End-to-end smoke test for health check endpoint."""
    with httpx.Client(base_url=api_base_url) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
