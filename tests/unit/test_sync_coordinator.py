"""Unit tests for SyncCoordinator class."""

from unittest.mock import Mock, patch

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

    @patch("builtins.print")
    def test_initial_setup_success(self, mock_print):
        """Test successful initial setup."""
        self.mock_git_manager.setup_repository.return_value = True

        expected_result = {
            "success": True,
            "message": "Setup completed",
            "stats": {"processed": 5, "failed": 0},
        }

        with patch.object(self.coordinator, "full_sync", return_value=expected_result):
            result = self.coordinator.initial_setup()

        assert result == expected_result
        self.mock_git_manager.setup_repository.assert_called_once()
        mock_print.assert_called_with("Starting initial setup...")

    @patch("builtins.print")
    def test_initial_setup_repo_failure(self, mock_print):
        """Test initial setup when repository setup fails."""
        self.mock_git_manager.setup_repository.return_value = False

        result = self.coordinator.initial_setup()

        expected = {"success": False, "error": "Failed to setup repository"}
        assert result == expected
        mock_print.assert_called_with("Starting initial setup...")

    @patch("builtins.print")
    def test_full_sync_no_files(self, mock_print):
        """Test full sync when no markdown files exist."""
        self.mock_git_manager.get_all_markdown_files.return_value = []

        result = self.coordinator.full_sync()

        expected = {
            "success": True,
            "message": "No markdown files found",
            "stats": {"processed": 0, "failed": 0},
        }
        assert result == expected
        mock_print.assert_called_with("Starting full synchronization...")

    @patch("builtins.print")
    def test_full_sync_success(self, mock_print):
        """Test successful full synchronization."""
        self.mock_git_manager.get_all_markdown_files.return_value = [
            "doc1.md",
            "doc2.md",
            "doc3.md",
        ]
        self.mock_git_manager.get_file_content.side_effect = [
            "Content 1",
            "Content 2",
            None,
        ]

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

        self.mock_processor.process_file.side_effect = [mock_doc1, mock_doc2, None]
        self.mock_processor.split_content_for_embedding.side_effect = [
            [{"content": "chunk1"}],
            [{"content": "chunk2"}],
        ]

        self.mock_vector_store.add_document.side_effect = [True, True]

        result = self.coordinator.full_sync()

        assert result["success"] is True
        assert result["stats"]["processed"] == 2
        assert result["stats"]["failed"] == 1
        assert result["stats"]["total_chunks"] == 2

    @patch("builtins.print")
    def test_full_sync_exception(self, mock_print):
        """Test full sync with exception."""
        self.mock_git_manager.get_all_markdown_files.side_effect = Exception(
            "Git error"
        )

        result = self.coordinator.full_sync()

        assert result["success"] is False
        assert "Git error" in result["error"]

    @patch("builtins.print")
    def test_incremental_sync_no_changes(self, mock_print):
        """Test incremental sync when no changes exist."""
        self.mock_git_manager.get_changed_files.return_value = []

        result = self.coordinator.incremental_sync()

        expected = {
            "success": True,
            "message": "No changes detected",
            "stats": {"processed": 0, "deleted": 0, "renamed": 0},
        }
        assert result == expected
        mock_print.assert_called_with("Starting incremental sync...")

    @patch("builtins.print")
    def test_incremental_sync_with_changes(self, mock_print):
        """Test incremental sync with file changes."""
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

        result = self.coordinator.incremental_sync()

        assert result["success"] is True
        assert result["stats"]["processed"] == 2
        assert result["stats"]["failed"] == 0
        assert result["stats"]["deleted"] == 1
        assert result["stats"]["total_chunks"] == 2
        assert len(result["changes"]) == 3

    @patch("builtins.print")
    def test_incremental_sync_pull_failure(self, mock_print):
        """Test incremental sync when git pull fails."""
        changes = [FileChange(file_path="doc1.md", status=FileStatus.MODIFIED)]
        self.mock_git_manager.get_changed_files.return_value = changes
        self.mock_git_manager.pull_changes.return_value = False
        self.mock_vector_store.process_file_changes.return_value = {}

        result = self.coordinator.incremental_sync()

        assert result["success"] is False
        assert result["error"] == "Failed to pull changes"

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
