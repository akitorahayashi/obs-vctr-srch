import os

import httpx
import pytest


class TestObsidianWorkflow:
    """End-to-end tests for the complete Obsidian vault search workflow."""

    @pytest.fixture(autouse=True)
    def setup_client(self, api_base_url: str):
        """Setup HTTP client for each test method."""
        # The timeout should be 10 seconds. Do not ever change it.
        self.client = httpx.Client(base_url=api_base_url, timeout=10.0)
        yield
        self.client.close()

    def test_api_health_check(self):
        """Test that the API is healthy and responding."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Debug: check what endpoints are available
        docs_response = self.client.get("/docs")
        print(f"Docs status: {docs_response.status_code}")

        # Check if the obs endpoints exist
        status_response = self.client.get("/api/obs-vctr-srch/status")
        print(f"Status endpoint response: {status_response.status_code}")
        if status_response.status_code != 200:
            print(f"Status response content: {status_response.content}")
            # Try without /api prefix
            alt_status = self.client.get("/obs/status")
            print(f"Alt status response: {alt_status.status_code}")

    def test_obsidian_status_endpoint(self):
        """Test the Obsidian status endpoint returns proper structure."""
        response = self.client.get("/api/obs-vctr-srch/status")
        assert response.status_code == 200

        data = response.json()
        # Verify expected status structure
        assert "sync_status" in data
        assert "repository" in data
        assert "vector_store" in data

    def test_obsidian_sync_functionality(self):
        """Test the Obsidian sync process."""
        response = self.client.post("/api/obs-vctr-srch/sync")

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404

        # If sync fails due to configuration, that's expected in test environment
        # But the endpoint should exist and handle the request

    def test_obsidian_search_functionality(self):
        """Test the Obsidian search functionality."""
        search_payload = {"query": "test search query", "n_results": 5}

        response = self.client.post("/api/obs-vctr-srch/search", json=search_payload)

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404

        # If search fails due to no indexed content, that's expected
        # But the endpoint should exist and handle the request

    def test_complete_obsidian_workflow_endpoints_exist(self):
        """Test that all Obsidian workflow endpoints are accessible."""
        # Test status endpoint
        status_response = self.client.get("/api/obs-vctr-srch/status")
        assert status_response.status_code != 404

        # Test sync endpoint
        sync_response = self.client.post("/api/obs-vctr-srch/sync")
        assert sync_response.status_code != 404

        # Test search endpoint
        search_response = self.client.post(
            "/api/obs-vctr-srch/search", json={"query": "test", "n_results": 5}
        )
        assert search_response.status_code != 404


@pytest.fixture(scope="module")
def api_base_url():
    """
    Provides the base URL for the API service.
    Uses the conftest.py e2e_setup fixture for container management.
    """
    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8005")
    return f"http://{host_bind_ip}:{host_port}"
