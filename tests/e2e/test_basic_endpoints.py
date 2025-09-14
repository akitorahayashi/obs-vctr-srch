"""
Basic API endpoint verification tests.
Tests fundamental API health and endpoint availability.
"""

from fastapi.testclient import TestClient


class TestBasicEndpoints:
    """Test basic API endpoint functionality."""

    def test_health_endpoints(self, client: TestClient):
        """Test that health endpoints are accessible."""
        # Main health check
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "ok"}

        # Obs-specific health check
        obs_health_response = client.get("/api/obs-vctr-srch/health")
        assert obs_health_response.status_code == 200

    def test_status_endpoint_structure(self, client: TestClient):
        """Test status endpoint returns proper structure."""
        response = client.get("/api/obs-vctr-srch/status")
        assert response.status_code == 200

        data = response.json()
        assert "sync_status" in data
        assert "repository" in data
        assert "vector_store" in data

    def test_all_public_endpoints_exist(self, client: TestClient):
        """Test that all public API endpoints are accessible (not 404)."""
        endpoints = [
            ("GET", "/health"),
            ("GET", "/docs"),
            ("GET", "/api/obs-vctr-srch/health"),
            ("GET", "/api/obs-vctr-srch/status"),
            ("POST", "/api/obs-vctr-srch/search"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                if "search" in endpoint:
                    response = client.post(
                        endpoint, json={"query": "test", "n_results": 1}
                    )
                else:
                    response = client.post(endpoint)

            assert response.status_code != 404, f"{method} {endpoint} returned 404"

    def test_admin_endpoints_removed_from_public_api(self, client: TestClient):
        """Test that admin endpoints have been properly removed from public API."""
        admin_endpoints = [
            "/api/obs-vctr-srch/sync",
            "/api/obs-vctr-srch/build-index",
        ]

        for endpoint in admin_endpoints:
            response = client.post(endpoint)
            assert (
                response.status_code == 404
            ), f"Admin endpoint {endpoint} should not exist in public API"

    def test_search_endpoint_structure(self, client: TestClient):
        """Test search endpoint returns proper structure (regardless of content)."""
        search_response = client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "test", "n_results": 1},
        )
        assert search_response.status_code == 200

        search_data = search_response.json()
        assert "results" in search_data
