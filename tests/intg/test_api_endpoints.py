import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestAPIEndpoints:
    """Integration tests for API endpoint validation."""

    def setup_method(self):
        """Setup test client for each test method."""
        self.client = TestClient(app)

    def teardown_method(self):
        """Close test client after each test method."""
        self.client.close()

    def test_health_check_endpoint(self):
        """Test health check endpoint functionality."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_obsidian_status_endpoint_exists(self):
        """Test that Obsidian status endpoint exists and returns proper structure."""
        response = self.client.get("/api/obs-vctr-srch/status")
        assert response.status_code == 200
        response_data = response.json()

        # Verify response structure
        assert "sync_status" in response_data
        assert "repository" in response_data
        assert "vector_store" in response_data

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/obs-vctr-srch/sync",
            "/api/obs-vctr-srch/build-index",
        ],
    )
    def test_admin_endpoints_removed_from_public_api(self, endpoint):
        """Test that admin endpoints have been removed from public API."""
        response = self.client.post(endpoint)
        assert (
            response.status_code == 404
        ), f"Admin endpoint {endpoint} should not exist in public API"

    def test_obsidian_search_endpoint_exists(self):
        """Test that Obsidian search endpoint exists."""
        response = self.client.post("/api/obs-vctr-srch/search", json={"query": "test"})
        assert response.status_code != 404

    @pytest.mark.parametrize(
        "endpoint,method",
        [
            ("/api/obs-vctr-srch/status", "GET"),
            ("/api/obs-vctr-srch/search", "POST"),
            ("/api/obs-vctr-srch/health", "GET"),
        ],
    )
    def test_api_endpoints_accessibility(self, endpoint, method):
        """Test that public API endpoints are properly loaded and accessible."""
        if method == "GET":
            response = self.client.get(endpoint)
        elif method == "POST":
            response = self.client.post(
                endpoint, json={"query": "test"} if "search" in endpoint else {}
            )

        assert (
            response.status_code != 404
        ), f"Endpoint {method} {endpoint} should exist in public API"

    @pytest.mark.parametrize(
        "payload,expected_status",
        [
            ({"query": ""}, [400, 422]),
            ({}, [400, 422]),
            (None, [400, 422]),
            ({"query": "test", "n_results": -1}, [400, 422]),
            ({"query": "test", "n_results": 9999}, [400, 422]),
        ],
    )
    def test_search_endpoint_error_handling(self, payload, expected_status):
        """Test search endpoint handles invalid requests properly."""
        response = self.client.post("/api/obs-vctr-srch/search", json=payload)
        assert (
            response.status_code in expected_status
        ), f"Request with {payload} should return client error"

    def test_status_endpoint_structure(self):
        """Test status endpoint returns consistent structure even on errors."""
        response = self.client.get("/api/obs-vctr-srch/status")
        assert response.status_code == 200

        data = response.json()
        # Should always have these keys, even if services fail
        required_keys = ["sync_status", "repository", "vector_store"]
        for key in required_keys:
            assert key in data, f"Status response should always include '{key}' key"
