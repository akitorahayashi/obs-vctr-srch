"""
Basic API endpoint verification tests.
Tests fundamental API health and endpoint availability.
"""

import os

import httpx
import pytest


class TestBasicEndpoints:
    """Test basic API endpoint functionality."""

    @pytest.fixture(autouse=True)
    def setup_client(self, api_base_url: str):
        """Setup HTTP client for each test method."""
        self.client = httpx.Client(base_url=api_base_url, timeout=60.0)
        yield
        self.client.close()

    def test_health_endpoints(self):
        """Test that health endpoints are accessible."""
        # Main health check
        health_response = self.client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "ok"}

        # Obs-specific health check
        obs_health_response = self.client.get("/api/obs-vctr-srch/health")
        assert obs_health_response.status_code == 200

    def test_status_endpoint_structure(self):
        """Test status endpoint returns proper structure."""
        response = self.client.get("/api/obs-vctr-srch/status")
        assert response.status_code == 200

        data = response.json()
        assert "sync_status" in data
        assert "repository" in data
        assert "vector_store" in data

    def test_all_endpoints_exist(self):
        """Test that all core endpoints are accessible (not 404)."""
        endpoints = [
            ("GET", "/health"),
            ("GET", "/docs"),
            ("GET", "/api/obs-vctr-srch/health"),
            ("GET", "/api/obs-vctr-srch/status"),
            ("POST", "/api/obs-vctr-srch/sync"),
            ("POST", "/api/obs-vctr-srch/build-index"),
            ("POST", "/api/obs-vctr-srch/search"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                if "search" in endpoint:
                    response = self.client.post(
                        endpoint, json={"query": "test", "n_results": 1}
                    )
                else:
                    response = self.client.post(endpoint)

            # Should not be 404 (endpoint exists)
            assert response.status_code != 404, f"{method} {endpoint} returned 404"

    def test_search_endpoint_structure(self):
        """Test search endpoint returns proper structure (regardless of content)."""
        search_response = self.client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "test", "n_results": 1},
        )
        assert search_response.status_code == 200

        search_data = search_response.json()
        assert "results" in search_data
        # Results may be empty - that's valid for basic endpoint verification


@pytest.fixture(scope="module")
def api_base_url():
    """Provides the base URL for the API service."""
    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8005")
    return f"http://{host_bind_ip}:{host_port}"
