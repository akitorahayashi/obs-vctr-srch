"""Tests for Admin app streaming endpoints."""

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.apps.admin.app import app


class TestAdminStreamingEndpoints:
    """Test streaming endpoints in admin app."""

    def test_sync_stream_endpoint_exists(self):
        """Test that sync stream endpoint exists in admin app."""
        client = TestClient(app)

        # Endpoint should exist but may fail due to missing dependencies
        response = client.post("/api/sync")
        assert response.status_code != 404  # Should exist

    def test_build_index_endpoint_exists(self):
        """Test that build index endpoint exists in admin app."""
        client = TestClient(app)

        # Endpoint should exist but may fail due to missing dependencies
        response = client.post("/api/build-index")
        assert response.status_code != 404  # Should exist

    @patch("src.apps.admin.app.get_sync_coordinator")
    def test_sync_stream_no_changes(self, mock_get_coordinator):
        """Test sync stream with no changes."""
        client = TestClient(app)

        # Mock the coordinator to return no changes
        mock_coordinator = Mock()

        async def mock_sync_stream():
            yield {
                "type": "status",
                "message": "Starting incremental sync...",
                "progress": 0,
            }
            yield {
                "type": "complete",
                "message": "No changes detected - sync up to date",
                "stats": {"processed": 0, "deleted": 0, "renamed": 0, "failed": 0},
            }

        mock_coordinator.incremental_sync_stream = mock_sync_stream
        mock_get_coordinator.return_value = mock_coordinator

        response = client.post("/api/sync")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

    @patch("src.apps.admin.app.get_sync_coordinator")
    def test_build_index_stream_success(self, mock_get_coordinator):
        """Test build index stream success scenario."""
        client = TestClient(app)

        # Mock the coordinator to return successful rebuild
        mock_coordinator = Mock()

        async def mock_rebuild_stream():
            yield {
                "type": "status",
                "message": "Starting build index process...",
                "progress": 0,
            }
            yield {
                "type": "status",
                "message": "Clearing existing index...",
                "progress": 10,
            }
            yield {
                "type": "complete",
                "message": "Build index complete! Processed 2 files, 0 failed",
                "stats": {"processed": 2, "failed": 0, "total_chunks": 5},
                "progress": 100,
            }

        mock_coordinator.rebuild_index_stream = mock_rebuild_stream
        mock_get_coordinator.return_value = mock_coordinator

        response = client.post("/api/build-index")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

    def test_admin_health_check(self):
        """Test admin app health check."""
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_build_index_monitor_page(self):
        """Test build index monitor page loads."""
        client = TestClient(app)

        response = client.get("/build-index-monitor")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
