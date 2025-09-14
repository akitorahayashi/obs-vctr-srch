"""Unit tests for SyncCoordinator class."""

from unittest.mock import patch

from src.services.git_manager import FileChange
from src.services.obsidian_processor import ObsidianDocument
from src.services.sync_coordinator import SyncCoordinator


class TestSyncCoordinator:
    """Test cases for SyncCoordinator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo_url = "https://github.com/test/repo.git"
        self.local_path = "/tmp/test_repo"
        self.vector_store_path = "./test_chroma_db"
        self.branch = "main"
        self.github_token = "test_token"

        with (
            patch("src.services.sync_coordinator.create_git_manager"),
            patch("src.services.sync_coordinator.ObsidianProcessor"),
            patch("src.services.sync_coordinator.VectorStore"),
        ):

            self.coordinator = SyncCoordinator(
                self.repo_url,
                self.local_path,
                self.vector_store_path,
                self.branch,
                self.github_token,
            )

    def test_init(self):
        """Test SyncCoordinator initialization."""
        assert str(self.coordinator.local_path) == self.local_path

    @patch("builtins.print")
    def test_initial_setup_success(self, mock_print):
        """Test successful initial setup."""
        self.coordinator.git_manager.setup_repository.return_value = True

        # Mock full_sync
        expected_result = {
            "success": True,
            "message": "Setup completed",
            "stats": {"processed": 5, "failed": 0},
        }

        with patch.object(self.coordinator, "full_sync", return_value=expected_result):
            result = self.coordinator.initial_setup()

        assert result == expected_result
        self.coordinator.git_manager.setup_repository.assert_called_once()
        mock_print.assert_called_with("Starting initial setup...")

    @patch("builtins.print")
    def test_initial_setup_repo_failure(self, mock_print):
        """Test initial setup when repository setup fails."""
        self.coordinator.git_manager.setup_repository.return_value = False

        result = self.coordinator.initial_setup()

        expected = {"success": False, "error": "Failed to setup repository"}
        assert result == expected
        mock_print.assert_called_with("Starting initial setup...")

    @patch("builtins.print")
    def test_initial_setup_repo_auth_failure(self, mock_print):
        """Test initial setup when repository authentication fails."""
        # Simulate authentication failure during setup
        self.coordinator.git_manager.setup_repository.return_value = False

        result = self.coordinator.initial_setup()

        # Should return failure and not proceed to full_sync
        expected = {"success": False, "error": "Failed to setup repository"}
        assert result == expected
        self.coordinator.git_manager.setup_repository.assert_called_once()
        # Verify full_sync is not called when repo setup fails
        with patch.object(self.coordinator, "full_sync") as mock_full_sync:
            self.coordinator.initial_setup()
            mock_full_sync.assert_not_called()

    @patch("builtins.print")
    def test_full_sync_no_files(self, mock_print):
        """Test full sync when no markdown files exist."""
        self.coordinator.git_manager.get_all_markdown_files.return_value = []

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
        # Mock git manager
        self.coordinator.git_manager.get_all_markdown_files.return_value = [
            "doc1.md",
            "doc2.md",
            "doc3.md",
        ]
        self.coordinator.git_manager.get_file_content.side_effect = [
            "Content 1",
            "Content 2",
            None,  # Third file fails to read
        ]

        # Mock processor
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

        self.coordinator.processor.process_file.side_effect = [
            mock_doc1,
            mock_doc2,
            None,
        ]
        self.coordinator.processor.split_content_for_embedding.side_effect = [
            [{"content": "chunk1"}],
            [{"content": "chunk2"}],
        ]

        # Mock vector store
        self.coordinator.vector_store.add_document.side_effect = [True, True]

        result = self.coordinator.full_sync()

        assert result["success"] is True
        assert result["stats"]["processed"] == 2
        assert result["stats"]["failed"] == 1
        assert result["stats"]["total_chunks"] == 2

    @patch("builtins.print")
    def test_full_sync_exception(self, mock_print):
        """Test full sync with exception."""
        self.coordinator.git_manager.get_all_markdown_files.side_effect = Exception(
            "Git error"
        )

        result = self.coordinator.full_sync()

        assert result["success"] is False
        assert "Git error" in result["error"]

    @patch("builtins.print")
    def test_incremental_sync_no_changes(self, mock_print):
        """Test incremental sync when no changes exist."""
        self.coordinator.git_manager.get_changed_files.return_value = []

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
        # Mock changes
        changes = [
            FileChange(file_path="doc1.md", change_type="M"),
            FileChange(file_path="doc2.md", change_type="A"),
            FileChange(file_path="doc3.md", change_type="D"),
        ]
        self.coordinator.git_manager.get_changed_files.return_value = changes
        self.coordinator.git_manager.pull_changes.return_value = True

        # Mock vector store change processing
        self.coordinator.vector_store.process_file_changes.return_value = {
            "deleted": 1,
            "renamed": 0,
        }

        # Mock file processing
        self.coordinator.git_manager.get_file_content.side_effect = [
            "Content 1",
            "Content 2",
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

        self.coordinator.processor.process_file.side_effect = [mock_doc1, mock_doc2]
        self.coordinator.processor.split_content_for_embedding.side_effect = [
            [{"content": "chunk1"}],
            [{"content": "chunk2"}],
        ]
        self.coordinator.vector_store.add_document.side_effect = [True, True]

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
        changes = [FileChange(file_path="doc1.md", change_type="M")]
        self.coordinator.git_manager.get_changed_files.return_value = changes
        self.coordinator.git_manager.pull_changes.return_value = False
        self.coordinator.vector_store.process_file_changes.return_value = {}

        result = self.coordinator.incremental_sync()

        assert result["success"] is False
        assert result["error"] == "Failed to pull changes"

    @patch("builtins.print")
    def test_incremental_sync_exception(self, mock_print):
        """Test incremental sync with exception."""
        self.coordinator.git_manager.get_changed_files.side_effect = Exception(
            "Sync error"
        )

        result = self.coordinator.incremental_sync()

        assert result["success"] is False
        assert "Sync error" in result["error"]

    def test_search_documents(self):
        """Test document search."""
        mock_results = [
            {"id": "1", "content": "Result 1"},
            {"id": "2", "content": "Result 2"},
        ]
        self.coordinator.vector_store.search.return_value = mock_results

        result = self.coordinator.search_documents(
            query="test query", n_results=5, file_filter="*.md", tag_filter=["tag1"]
        )

        assert result == mock_results
        self.coordinator.vector_store.search.assert_called_once_with(
            query="test query", n_results=5, file_filter="*.md", tag_filter=["tag1"]
        )

    def test_get_repository_status_success(self):
        """Test getting repository status successfully."""
        # Mock git manager
        self.coordinator.git_manager.get_last_sync_info.return_value = {
            "commit_hash": "abc123",
            "commit_date": "2023-01-01T10:00:00",
            "commit_message": "Latest commit",
        }
        self.coordinator.git_manager.get_all_markdown_files.return_value = [
            "doc1.md",
            "doc2.md",
        ]

        # Mock vector store
        self.coordinator.vector_store.get_stats.return_value = {
            "total_documents": 2,
            "total_chunks": 10,
        }

        result = self.coordinator.get_repository_status()

        assert result["repository"]["url"] == self.coordinator.git_manager.repo_url
        assert result["repository"]["total_md_files"] == 2
        assert result["vector_store"]["total_documents"] == 2
        assert result["sync_status"] == "ready"

    def test_get_repository_status_exception(self):
        """Test getting repository status with exception."""
        self.coordinator.git_manager.get_last_sync_info.side_effect = Exception(
            "Status error"
        )

        result = self.coordinator.get_repository_status()

        assert "error" in result
        assert "Status error" in result["error"]

    def test_cleanup_orphaned_embeddings_none_found(self):
        """Test cleanup when no orphaned embeddings exist."""
        self.coordinator.vector_store.list_all_documents.return_value = [
            "doc1.md",
            "doc2.md",
        ]
        self.coordinator.git_manager.get_all_markdown_files.return_value = [
            "doc1.md",
            "doc2.md",
        ]

        result = self.coordinator.cleanup_orphaned_embeddings()

        expected = {"removed": 0, "message": "No orphaned embeddings found"}
        assert result == expected

    def test_cleanup_orphaned_embeddings_found(self):
        """Test cleanup when orphaned embeddings exist."""
        self.coordinator.vector_store.list_all_documents.return_value = [
            "doc1.md",
            "doc2.md",
            "orphan.md",
        ]
        self.coordinator.git_manager.get_all_markdown_files.return_value = [
            "doc1.md",
            "doc2.md",
        ]
        self.coordinator.vector_store.remove_document.return_value = True

        result = self.coordinator.cleanup_orphaned_embeddings()

        assert result["removed"] == 1
        assert result["total_orphaned"] == 1
        assert "Removed 1 orphaned embeddings" in result["message"]
        self.coordinator.vector_store.remove_document.assert_called_once_with(
            "orphan.md"
        )

    def test_cleanup_orphaned_embeddings_exception(self):
        """Test cleanup with exception."""
        self.coordinator.vector_store.list_all_documents.side_effect = Exception(
            "Cleanup error"
        )

        result = self.coordinator.cleanup_orphaned_embeddings()

        assert "error" in result
        assert "Cleanup error" in result["error"]

    def test_force_reindex_file_success(self):
        """Test successful file re-indexing."""
        file_path = "test.md"
        content = "Test content"

        self.coordinator.git_manager.get_file_content.return_value = content

        mock_doc = ObsidianDocument(
            file_path=file_path,
            title="Test",
            content=content,
            metadata={},
            tags=[],
            links=[],
        )
        self.coordinator.processor.process_file.return_value = mock_doc

        chunks = [{"content": "chunk1"}, {"content": "chunk2"}]
        self.coordinator.processor.split_content_for_embedding.return_value = chunks

        self.coordinator.vector_store.add_document.return_value = True

        result = self.coordinator.force_reindex_file(file_path)

        assert result["success"] is True
        assert result["chunks"] == 2
        assert f"Re-indexed {file_path}" in result["message"]

    def test_force_reindex_file_not_found(self):
        """Test re-indexing when file is not found."""
        file_path = "nonexistent.md"
        self.coordinator.git_manager.get_file_content.return_value = None

        result = self.coordinator.force_reindex_file(file_path)

        assert result["success"] is False
        assert f"File not found: {file_path}" in result["error"]

    def test_force_reindex_file_process_failure(self):
        """Test re-indexing when file processing fails."""
        file_path = "test.md"
        self.coordinator.git_manager.get_file_content.return_value = "content"
        self.coordinator.processor.process_file.return_value = None

        result = self.coordinator.force_reindex_file(file_path)

        assert result["success"] is False
        assert f"Failed to process file: {file_path}" in result["error"]

    def test_force_reindex_file_vector_store_failure(self):
        """Test re-indexing when vector store add fails."""
        file_path = "test.md"
        content = "Test content"

        self.coordinator.git_manager.get_file_content.return_value = content

        mock_doc = ObsidianDocument(
            file_path=file_path,
            title="Test",
            content=content,
            metadata={},
            tags=[],
            links=[],
        )
        self.coordinator.processor.process_file.return_value = mock_doc
        self.coordinator.processor.split_content_for_embedding.return_value = [
            {"content": "chunk"}
        ]
        self.coordinator.vector_store.add_document.return_value = False

        result = self.coordinator.force_reindex_file(file_path)

        assert result["success"] is False
        assert f"Failed to add to vector store: {file_path}" in result["error"]

    def test_force_reindex_file_exception(self):
        """Test re-indexing with exception."""
        file_path = "test.md"
        self.coordinator.git_manager.get_file_content.side_effect = Exception(
            "Reindex error"
        )

        result = self.coordinator.force_reindex_file(file_path)

        assert result["success"] is False
        assert "Reindex error" in result["error"]
