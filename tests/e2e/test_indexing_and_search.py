"""
Search functionality tests - admin operations have been moved to admin app.
"""

from fastapi.testclient import TestClient


class TestSearchFunctionality:
    """Test search functionality without admin operations."""

    def test_removed_build_index_endpoint(self, client: TestClient):
        """Test that build-index endpoint has been removed from public API."""
        build_response = client.post("/api/obs-vctr-srch/build-index")
        assert build_response.status_code == 404  # Should not exist in public API

    def test_search_endpoint_exists(self, client: TestClient):
        """Test that search endpoint still exists but may return empty results."""
        search_response = client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "test", "n_results": 1},
        )
        # Search endpoint should exist (not 404) but may return empty results or error without data
        assert search_response.status_code != 404

        # If successful, should have proper structure
        if search_response.status_code == 200:
            search_data = search_response.json()
            assert "results" in search_data

    def test_search_parameters_validation(self, client: TestClient):
        """Test search parameter validation."""
        search_response = client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "API", "n_results": 1},
        )
        # Should validate parameters properly (not 404)
        assert search_response.status_code != 404

    def test_empty_query_handling(self, client: TestClient):
        """Test search behavior with edge cases."""
        search_response = client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "", "n_results": 5},
        )
        assert search_response.status_code == 400

    def test_admin_endpoints_removed(self, client: TestClient):
        """Test that admin endpoints have been properly removed from public API."""
        admin_endpoints = [
            "/api/obs-vctr-srch/build-index",
            "/api/obs-vctr-srch/build-index-stream",
            "/api/obs-vctr-srch/sync",
        ]

        for endpoint in admin_endpoints:
            response = client.post(endpoint)
            assert (
                response.status_code == 404
            ), f"Admin endpoint {endpoint} should not exist in public API"
