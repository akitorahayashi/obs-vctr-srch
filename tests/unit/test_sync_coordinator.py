"""Unit tests for SyncCoordinator class."""

from unittest.mock import Mock

import pytest

from src.models import GitManager, ObsidianProcessor, VectorStore
from src.models.obsidian_processor import ObsidianDocument
from src.schemas import FileChange, FileStatus
from src.services import SyncCoordinator


class TestSyncCoordinator:
    """Test cases for SyncCoordinator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_git_manager = Mock(spec=GitManager)
        self.mock_vector_store = Mock(spec=VectorStore)
        self.mock_processor = Mock(spec=ObsidianProcessor)

        self.coordinator = SyncCoordinator(
            git_manager=self.mock_git_manager,
            vector_store=self.mock_vector_store,
            processor=self.mock_processor,
        )

    def test_init(self):
        """Test SyncCoordinator initialization."""
        assert self.coordinator.git_manager == self.mock_git_manager
        assert self.coordinator.vector_store == self.mock_vector_store
        assert self.coordinator.processor == self.mock_processor

    @pytest.mark.asyncio
    async def test_incremental_sync_stream_no_changes(self):
        """Test incremental sync stream when no changes exist."""
        self.mock_git_manager.get_changed_files.return_value = []

        results = []
        async for progress in self.coordinator.incremental_sync_stream():
            results.append(progress)

        # Should get start message and complete message
        assert len(results) >= 2
        assert results[0]["type"] == "status"
        assert "Starting incremental sync" in results[0]["message"]

        final_result = results[-1]
        assert final_result["type"] == "complete"
        assert "No changes detected" in final_result["message"]
        assert final_result["stats"]["processed"] == 0
        assert final_result["stats"]["deleted"] == 0
        assert final_result["stats"]["renamed"] == 0

    @pytest.mark.asyncio
    async def test_incremental_sync_stream_with_changes(self):
        """Test incremental sync stream with file changes."""
        changes = [
            FileChange(file_path="doc1.md", status=FileStatus.MODIFIED),
            FileChange(file_path="doc2.md", status=FileStatus.ADDED),
            FileChange(file_path="doc3.md", status=FileStatus.DELETED),
        ]
        self.mock_git_manager.get_changed_files.return_value = changes
        self.mock_git_manager.pull_changes.return_value = True

        self.mock_vector_store.process_file_changes.return_value = {
            "deleted": 1,
            "renamed": 0,
        }

        self.mock_git_manager.get_file_content.side_effect = ["Content 1", "Content 2"]

        mock_doc1 = ObsidianDocument(
            file_path="doc1.md",
            title="Doc 1",
            content="Content 1",
            metadata={},
            tags=[],
            links=[],
        )
        mock_doc2 = ObsidianDocument(
            file_path="doc2.md",
            title="Doc 2",
            content="Content 2",
            metadata={},
            tags=[],
            links=[],
        )

        self.mock_processor.process_file.side_effect = [mock_doc1, mock_doc2]
        self.mock_processor.split_content_for_embedding.side_effect = [
            [{"content": "chunk1"}],
            [{"content": "chunk2"}],
        ]
        self.mock_vector_store.add_document.side_effect = [True, True]

        results = []
        async for progress in self.coordinator.incremental_sync_stream():
            results.append(progress)

        # Find the final completion result
        final_result = None
        for result in results:
            if result["type"] == "complete":
                final_result = result
                break

        assert final_result is not None
        assert final_result["stats"]["processed"] == 2
        assert final_result["stats"]["failed"] == 0
        assert final_result["stats"]["deleted"] == 1
        assert final_result["stats"]["total_chunks"] == 2

    @pytest.mark.asyncio
    async def test_incremental_sync_stream_pull_failure(self):
        """Test incremental sync stream when git pull fails."""
        changes = [FileChange(file_path="doc1.md", status=FileStatus.MODIFIED)]
        self.mock_git_manager.get_changed_files.return_value = changes
        self.mock_git_manager.pull_changes.return_value = False
        self.mock_vector_store.process_file_changes.return_value = {}

        results = []
        async for progress in self.coordinator.incremental_sync_stream():
            results.append(progress)

        # Should get error message
        error_result = None
        for result in results:
            if result["type"] == "error":
                error_result = result
                break

        assert error_result is not None
        assert "Failed to pull changes" in error_result["message"]

    @pytest.mark.asyncio
    async def test_rebuild_index_stream(self):
        """Test rebuild index stream functionality."""
        # Mock repository setup
        self.mock_git_manager.repo = None
        self.mock_git_manager.setup_repository.return_value = True

        # Mock clear collection
        self.mock_vector_store.clear_collection.return_value = {"success": True}

        # Mock markdown files
        self.mock_git_manager.get_all_markdown_files.return_value = [
            "doc1.md",
            "doc2.md",
        ]
        self.mock_git_manager.get_file_content.side_effect = ["Content 1", "Content 2"]

        # Mock processing
        mock_doc1 = ObsidianDocument(
            file_path="doc1.md",
            title="Doc 1",
            content="Content 1",
            metadata={},
            tags=[],
            links=[],
        )
        mock_doc2 = ObsidianDocument(
            file_path="doc2.md",
            title="Doc 2",
            content="Content 2",
            metadata={},
            tags=[],
            links=[],
        )

        self.mock_processor.process_file.side_effect = [mock_doc1, mock_doc2]
        self.mock_processor.split_content_for_embedding.side_effect = [
            [{"content": "chunk1"}],
            [{"content": "chunk2"}],
        ]
        self.mock_vector_store.add_document.side_effect = [True, True]

        results = []
        async for progress in self.coordinator.rebuild_index_stream():
            results.append(progress)

        # Should have various progress updates and final completion
        assert len(results) > 5  # Multiple progress updates expected

        # Find completion result
        final_result = None
        for result in results:
            if result["type"] == "complete":
                final_result = result
                break

        assert final_result is not None
        assert final_result["stats"]["processed"] == 2
        assert final_result["stats"]["failed"] == 0

    def test_search_documents(self):
        """Test document search."""
        mock_results = [
            {"id": "1", "content": "Result 1"},
            {"id": "2", "content": "Result 2"},
        ]
        self.mock_vector_store.search.return_value = mock_results

        result = self.coordinator.search_documents(
            query="test query", n_results=5, file_filter="*.md", tag_filter=["tag1"]
        )

        assert result == mock_results
        self.mock_vector_store.search.assert_called_once_with(
            query="test query", n_results=5, file_filter="*.md", tag_filter=["tag1"]
        )
