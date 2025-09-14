"""
Indexing and search functionality tests with mock data.
Tests vector store operations using lightweight mock documents.
"""

import os

import httpx
import pytest


class TestIndexingAndSearch:
    """Test indexing and search functionality with mock data."""

    @pytest.fixture(autouse=True)
    def setup_client(self, api_base_url: str):
        """Setup HTTP client for indexing tests."""
        self.client = httpx.Client(base_url=api_base_url, timeout=300.0)
        yield
        self.client.close()

    def test_build_index_workflow(self):
        """Test complete build-index workflow with mock data."""
        # Trigger full index build
        build_response = self.client.post("/api/obs-vctr-srch/build-index")
        assert build_response.status_code == 200

        # Verify status shows indexed documents
        status_response = self.client.get("/api/obs-vctr-srch/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert "vector_store" in status_data

        vector_info = status_data.get("vector_store", {})
        document_count = vector_info.get("total_documents", 0)

        # Should have indexed our mock documents
        assert document_count > 0
        print(f"✅ Build-index completed: {document_count} documents indexed")

    def test_semantic_search_functionality(self):
        """Test semantic search with known mock content."""
        # Ensure data is indexed
        build_response = self.client.post("/api/obs-vctr-srch/build-index")
        assert build_response.status_code == 200

        # Test search with content we know exists in mock files
        search_tests = [
            {"query": "semantic search", "expected_min": 1},
            {"query": "FastAPI endpoints", "expected_min": 1},
            {"query": "Docker deployment", "expected_min": 1},
        ]

        for test in search_tests:
            search_response = self.client.post(
                "/api/obs-vctr-srch/search",
                json={"query": test["query"], "n_results": 5},
            )
            assert search_response.status_code == 200

            search_data = search_response.json()
            assert "results" in search_data
            results = search_data["results"]

            # Should find relevant content in mock docs
            assert len(results) >= test["expected_min"]
            print(f"✅ Search '{test['query']}': {len(results)} results")

            # Verify result structure
            if results:
                result = results[0]
                assert "content" in result
                assert "distance" in result
                # Additional fields that may be present
                assert any(
                    field in result
                    for field in ["metadata", "chunk_index", "file_path"]
                )

    def test_search_parameters(self):
        """Test search with different parameters."""
        # Ensure data is indexed
        build_response = self.client.post("/api/obs-vctr-srch/build-index")
        assert build_response.status_code == 200

        # Test different n_results values
        for n_results in [1, 3, 10]:
            search_response = self.client.post(
                "/api/obs-vctr-srch/search",
                json={"query": "API", "n_results": n_results},
            )
            assert search_response.status_code == 200

            results = search_response.json()["results"]
            # Should not return more than requested or available
            assert len(results) <= n_results

    def test_empty_query_handling(self):
        """Test search behavior with edge cases."""
        edge_cases = [
            {"query": "", "n_results": 5},
            {"query": "nonexistent_term_unlikely_to_match", "n_results": 5},
        ]

        for case in edge_cases:
            search_response = self.client.post("/api/obs-vctr-srch/search", json=case)
            # Should handle gracefully (200 or appropriate error)
            assert search_response.status_code in [200, 400, 422]

            if search_response.status_code == 200:
                search_data = search_response.json()
                assert "results" in search_data


@pytest.fixture(scope="module")
def api_base_url():
    """Provides the base URL for the API service using test configuration."""
    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8005")
    return f"http://{host_bind_ip}:{host_port}"
