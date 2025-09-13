"""
Production startup integration test.
Tests the critical path: clean container -> auth clone -> initial indexing -> API ready
"""

import os

import httpx
import pytest


class TestProductionStartup:
    """Test production startup sequence from clean state."""

    @pytest.fixture(autouse=True)
    def setup_client(self, api_base_url: str):
        """Setup HTTP client for each test method."""
        self.client = httpx.Client(
            base_url=api_base_url, timeout=600.0
        )  # 10 minutes for build-index
        yield
        self.client.close()

    def test_production_startup_with_auth_clone(self):
        """
        Test production startup: verify build-index can clone repository successfully.
        This test verifies the build-index endpoint sets up repository correctly.
        """
        # Verify required env vars are set for this test
        required_vars = ["OBSIDIAN_REPO_URL", "OBS_VAULT_TOKEN"]
        for var in required_vars:
            if not os.getenv(var):
                pytest.skip(f"Required environment variable {var} not set")

        # Manually trigger repository setup (clone verification only)
        build_response = self.client.post("/api/obs-vctr-srch/build-index")
        assert build_response.status_code == 200

        # Verify repo clone succeeded by checking status
        status_response = self.client.get("/api/obs-vctr-srch/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert "repository" in status_data
        assert "vector_store" in status_data

        # Should have commit info after successful setup
        repo_info = status_data.get("repository", {})
        assert "commit_hash" in repo_info or repo_info.get("status") == "available"

    def test_search_endpoints_available_after_clone(self):
        """Test that search endpoints are accessible after repository setup."""
        # Verify required env vars are set for this test
        required_vars = ["OBSIDIAN_REPO_URL", "OBS_VAULT_TOKEN"]
        for var in required_vars:
            if not os.getenv(var):
                pytest.skip(f"Required environment variable {var} not set")

        # First setup the repository (as admin would do)
        build_response = self.client.post("/api/obs-vctr-srch/build-index")
        assert build_response.status_code == 200

        # Verify search endpoint is accessible (but don't require actual results)
        search_response = self.client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "test", "n_results": 1},
        )
        assert search_response.status_code == 200

        search_data = search_response.json()
        assert "results" in search_data
        # Results may be empty - that's valid for clone verification


@pytest.fixture(scope="module")
def api_base_url():
    """
    Provides the base URL for the API service.
    Uses the conftest.py e2e_setup fixture for container management.
    """
    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8005")
    return f"http://{host_bind_ip}:{host_port}"
