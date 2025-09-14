from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.dependencies import get_git_manager, get_vector_store
from src.main import app
from src.models import GitManager, VectorStore
from src.schemas import FileChange, FileStatus, SearchResult


def get_mock_git_manager():
    """Override for get_git_manager dependency."""
    mock_gm = Mock(spec=GitManager)
    mock_gm.get_changed_files.return_value = [
        FileChange(status=FileStatus.ADDED, file_path="test.md")
    ]
    mock_gm.pull_changes.return_value = True
    mock_gm.get_all_markdown_files.return_value = ["test.md"]
    mock_gm.get_file_content.return_value = "# Test Document\n\nThis is a test."
    mock_gm.setup_repository.return_value = True
    return mock_gm


def get_mock_vector_store():
    """Override for get_vector_store dependency."""
    mock_vs = Mock(spec=VectorStore)
    mock_vs.search.return_value = [
        SearchResult(
            id="test.md#chunk_0",
            content="This is a test.",
            distance=0.1,
            file_path="test.md",
            title="Test Document",
            chunk_index=0,
            tags=[],
            links=[],
        )
    ]
    mock_vs.add_document.return_value = True
    mock_vs.process_file_changes.return_value = {
        "added": 0,
        "updated": 0,
        "deleted": 0,
        "renamed": 0,
    }
    mock_vs.clear_collection.return_value = {"success": True}
    return mock_vs


@pytest.fixture(scope="module")
def client() -> TestClient:
    """
    Test client fixture with dependency overrides for E2E tests.
    """
    app.dependency_overrides[get_git_manager] = get_mock_git_manager
    app.dependency_overrides[get_vector_store] = get_mock_vector_store

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides = {}  # Clear overrides after tests
