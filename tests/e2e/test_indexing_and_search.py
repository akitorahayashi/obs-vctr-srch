"""
Indexing and search functionality tests with mock data.
"""

from fastapi.testclient import TestClient


class TestIndexingAndSearch:
    """Test indexing and search functionality with mock data."""

    def test_build_index_workflow(self, client: TestClient):
        """Test complete build-index workflow with mock data."""
        build_response = client.post("/api/obs-vctr-srch/build-index")
        assert build_response.status_code == 200

        data = build_response.json()
        assert data["success"] is True
        assert data["stats"]["processed"] > 0

    def test_semantic_search_functionality(self, client: TestClient):
        """Test semantic search with known mock content."""
        client.post("/api/obs-vctr-srch/build-index")

        search_response = client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "test", "n_results": 1},
        )
        assert search_response.status_code == 200

        search_data = search_response.json()
        assert "results" in search_data
        results = search_data["results"]
        assert len(results) > 0
        assert results[0]["content"] == "This is a test."
        assert results[0]["file_path"] == "test.md"

    def test_search_parameters(self, client: TestClient):
        """Test search with different parameters."""
        client.post("/api/obs-vctr-srch/build-index")

        search_response = client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "API", "n_results": 1},
        )
        assert search_response.status_code == 200
        results = search_response.json()["results"]
        assert len(results) <= 1

    def test_empty_query_handling(self, client: TestClient):
        """Test search behavior with edge cases."""
        search_response = client.post(
            "/api/obs-vctr-srch/search",
            json={"query": "", "n_results": 5},
        )
        assert search_response.status_code == 400
