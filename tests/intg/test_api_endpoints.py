from fastapi.testclient import TestClient

from src.main import app


class TestAPIEndpoints:
    """Integration tests for API endpoint validation."""

    def setup_method(self):
        """Setup test client for each test method."""
        self.client = TestClient(app)

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

    def test_obsidian_sync_endpoint_exists(self):
        """Test that Obsidian sync endpoint exists."""
        response = self.client.post("/api/obs-vctr-srch/sync")
        assert response.status_code != 404

    def test_obsidian_search_endpoint_exists(self):
        """Test that Obsidian search endpoint exists."""
        response = self.client.post("/api/obs-vctr-srch/search", json={"query": "test"})
        assert response.status_code != 404

    def test_api_endpoints_accessibility(self):
        """Test that all API endpoints are properly loaded and accessible."""
        endpoints_to_test = [
            ("/api/obs-vctr-srch/status", "GET"),
            ("/api/obs-vctr-srch/sync", "POST"),
            ("/api/obs-vctr-srch/search", "POST"),
        ]

        for endpoint, method in endpoints_to_test:
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                response = self.client.post(
                    endpoint, json={"query": "test"} if "search" in endpoint else {}
                )

            # Should not be 404 (endpoint exists)
            assert (
                response.status_code != 404
            ), f"Endpoint {method} {endpoint} should exist"
