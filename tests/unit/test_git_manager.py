"""Unit tests for GitManager class."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from src.models import FileChange
from src.services.git_manager import GitManager


class TestGitManager:
    """Test cases for GitManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo_url = "https://github.com/test/repo.git"
        self.local_path = "/tmp/test_repo"
        self.branch = "main"
        self.github_token = "test_token"
        self.git_manager = GitManager(
            self.repo_url, self.local_path, self.branch, self.github_token
        )

    def test_init(self):
        """Test GitManager initialization."""
        assert self.git_manager.repo_url == self.repo_url
        assert self.git_manager.local_path == Path(self.local_path)
        assert self.git_manager.branch == self.branch
        assert self.git_manager.github_token == self.github_token
        assert self.git_manager.repo is None

    def test_build_clone_url_with_token(self):
        """Test building clone URL with GitHub token."""
        expected = "https://test_token@github.com/test/repo.git"
        result = self.git_manager._build_clone_url()
        assert result == expected

    def test_build_clone_url_without_token(self):
        """Test building clone URL without token."""
        self.git_manager.github_token = ""
        result = self.git_manager._build_clone_url()
        assert result == self.repo_url

    def test_build_clone_url_non_github(self):
        """Test building clone URL for non-GitHub repository."""
        self.git_manager.repo_url = "https://gitlab.com/test/repo.git"
        result = self.git_manager._build_clone_url()
        assert result == "https://gitlab.com/test/repo.git"

    @patch("src.services.git_manager.Repo")
    @patch("pathlib.Path.exists")
    def test_setup_repository_existing_repo(self, mock_exists, mock_repo_class):
        """Test setup when repository already exists."""

        # Mock existing repository - both local_path and .git should exist
        def mock_exists_func():
            path_str = str(self)
            return "test_repo" in path_str or ".git" in path_str

        mock_exists.return_value = True
        mock_repo = Mock()
        mock_repo.submodules = []  # Mock empty submodules
        mock_repo_class.return_value = mock_repo

        result = self.git_manager.setup_repository()

        assert result is True
        assert self.git_manager.repo == mock_repo
        mock_repo_class.assert_called_once_with(self.git_manager.local_path)

    @patch("src.services.git_manager.Repo")
    @patch("pathlib.Path.exists")
    def test_setup_repository_clone_new(self, mock_exists, mock_repo_class):
        """Test setup when cloning new repository."""
        mock_exists.return_value = False
        mock_repo = Mock()
        mock_repo.submodules = []  # Mock empty submodules
        mock_repo_class.clone_from.return_value = mock_repo

        result = self.git_manager.setup_repository()

        assert result is True
        assert self.git_manager.repo == mock_repo
        mock_repo_class.clone_from.assert_called_once_with(
            "https://test_token@github.com/test/repo.git",
            self.git_manager.local_path,
            branch=self.branch,
        )

    @patch("src.services.git_manager.Repo")
    @patch("pathlib.Path.exists")
    def test_setup_repository_failure(self, mock_exists, mock_repo_class):
        """Test setup repository failure."""
        mock_exists.return_value = False
        mock_repo_class.clone_from.side_effect = Exception("Clone failed")

        result = self.git_manager.setup_repository()

        assert result is False
        assert self.git_manager.repo is None

    @patch("src.services.git_manager.Repo")
    @patch("pathlib.Path.exists")
    def test_setup_repository_authentication_error(self, mock_exists, mock_repo_class):
        """Test setup repository with authentication error."""
        from git.exc import GitCommandError

        mock_exists.return_value = False
        # Simulate authentication failure
        mock_repo_class.clone_from.side_effect = GitCommandError(
            "git clone", 128, "Authentication failed"
        )

        result = self.git_manager.setup_repository()

        assert result is False
        assert self.git_manager.repo is None
        # Verify clone was attempted with correct URL
        mock_repo_class.clone_from.assert_called_once_with(
            "https://test_token@github.com/test/repo.git",
            self.git_manager.local_path,
            branch=self.branch,
        )

    @patch("src.services.git_manager.Repo")
    @patch("pathlib.Path.exists")
    def test_setup_repository_network_error(self, mock_exists, mock_repo_class):
        """Test setup repository with network error."""
        from git.exc import GitCommandError

        mock_exists.return_value = False
        # Simulate network failure
        mock_repo_class.clone_from.side_effect = GitCommandError(
            "git clone", 128, "Could not resolve host"
        )

        result = self.git_manager.setup_repository()

        assert result is False
        assert self.git_manager.repo is None

    def test_get_changed_files_no_repo(self):
        """Test getting changed files when repository is not initialized."""
        with pytest.raises(RuntimeError, match="Repository not initialized"):
            self.git_manager.get_changed_files()

    @patch("builtins.print")
    def test_get_changed_files_no_changes(self, mock_print):
        """Test getting changed files when no changes exist."""
        # Mock repository setup
        mock_repo = Mock()
        mock_origin = Mock()
        mock_local_commit = Mock()
        mock_remote_commit = Mock()

        mock_local_commit.hexsha = "abc123"
        mock_remote_commit.hexsha = "abc123"

        mock_origin.refs = {"main": Mock(commit=mock_remote_commit)}
        mock_repo.remotes.origin = mock_origin
        mock_repo.head.commit = mock_local_commit

        self.git_manager.repo = mock_repo

        result = self.git_manager.get_changed_files()

        assert result == []
        mock_origin.fetch.assert_called_once()
        mock_print.assert_called_with("No changes detected")

    def test_get_changed_files_with_changes(self):
        """Test getting changed files when changes exist."""
        # Mock repository setup
        mock_repo = Mock()
        mock_origin = Mock()
        mock_local_commit = Mock()
        mock_remote_commit = Mock()

        mock_local_commit.hexsha = "abc123"
        mock_remote_commit.hexsha = "def456"

        mock_origin.refs = {"main": Mock(commit=mock_remote_commit)}
        mock_repo.remotes.origin = mock_origin
        mock_repo.head.commit = mock_local_commit

        # Mock diff items
        mock_diff_item1 = Mock()
        mock_diff_item1.change_type = "M"
        mock_diff_item1.a_path = "test1.md"
        mock_diff_item1.b_path = "test1.md"
        mock_diff_item1.renamed_file = False

        mock_diff_item2 = Mock()
        mock_diff_item2.change_type = "A"
        mock_diff_item2.a_path = None
        mock_diff_item2.b_path = "test2.md"
        mock_diff_item2.renamed_file = False

        mock_diff_item3 = Mock()
        mock_diff_item3.change_type = "M"
        mock_diff_item3.a_path = "test3.py"
        mock_diff_item3.b_path = "test3.py"
        mock_diff_item3.renamed_file = False

        mock_local_commit.diff.return_value = [
            mock_diff_item1,
            mock_diff_item2,
            mock_diff_item3,
        ]

        self.git_manager.repo = mock_repo

        result = self.git_manager.get_changed_files()

        expected = [
            FileChange(file_path="test1.md", change_type="M", old_file_path=None),
            FileChange(file_path="test2.md", change_type="A", old_file_path=None),
        ]

        assert len(result) == 2
        assert result[0].file_path == expected[0].file_path
        assert result[0].change_type == expected[0].change_type
        assert result[1].file_path == expected[1].file_path
        assert result[1].change_type == expected[1].change_type

    def test_pull_changes_no_repo(self):
        """Test pulling changes when repository is not initialized."""
        with pytest.raises(RuntimeError, match="Repository not initialized"):
            self.git_manager.pull_changes()

    @patch("builtins.print")
    def test_pull_changes_success(self, mock_print):
        """Test successful pulling of changes."""
        mock_repo = Mock()
        mock_origin = Mock()
        mock_repo.remotes.origin = mock_origin
        mock_repo.submodules = []  # Mock empty submodules

        self.git_manager.repo = mock_repo

        result = self.git_manager.pull_changes()

        assert result is True
        mock_origin.pull.assert_called_once()
        # Check that both print statements were called
        expected_calls = [
            call("Successfully pulled latest changes"),
            call("Successfully updated all submodules"),
        ]
        mock_print.assert_has_calls(expected_calls)

    @patch("builtins.print")
    def test_pull_changes_failure(self, mock_print):
        """Test failure when pulling changes."""
        mock_repo = Mock()
        mock_origin = Mock()
        mock_origin.pull.side_effect = Exception("Pull failed")
        mock_repo.remotes.origin = mock_origin

        self.git_manager.repo = mock_repo

        result = self.git_manager.pull_changes()

        assert result is False
        mock_print.assert_called_with(
            "Failed to pull changes or update submodules: Pull failed"
        )

    def test_get_file_content_success(self):
        """Test successful file content retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.git_manager.local_path = Path(temp_dir)

            # Create test file
            test_file = Path(temp_dir) / "test.md"
            test_content = "# Test Document\n\nThis is a test."
            test_file.write_text(test_content, encoding="utf-8")

            result = self.git_manager.get_file_content("test.md")

            assert result == test_content

    def test_get_file_content_not_found(self):
        """Test file content retrieval when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.git_manager.local_path = Path(temp_dir)

            result = self.git_manager.get_file_content("nonexistent.md")

            assert result is None

    @patch("builtins.print")
    def test_get_file_content_error(self, mock_print):
        """Test file content retrieval with read error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.git_manager.local_path = Path(temp_dir)

            # Create test file path
            test_file = Path(temp_dir) / "test.md"
            test_file.write_text("content")

            # Mock read_text to raise exception
            with patch.object(Path, "read_text", side_effect=Exception("Read error")):
                result = self.git_manager.get_file_content("test.md")

            assert result is None
            mock_print.assert_called_with("Failed to read file test.md: Read error")

    def test_get_all_markdown_files(self):
        """Test getting all markdown files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.git_manager.local_path = Path(temp_dir)

            # Create test files
            (Path(temp_dir) / "test1.md").write_text("content1")
            (Path(temp_dir) / "test2.md").write_text("content2")
            (Path(temp_dir) / "subdir").mkdir()
            (Path(temp_dir) / "subdir" / "test3.md").write_text("content3")
            (Path(temp_dir) / "test.txt").write_text("not markdown")

            result = self.git_manager.get_all_markdown_files()

            expected = ["subdir/test3.md", "test1.md", "test2.md"]
            assert sorted(result) == sorted(expected)

    def test_get_all_markdown_files_no_directory(self):
        """Test getting markdown files when directory doesn't exist."""
        self.git_manager.local_path = Path("/nonexistent/path")

        result = self.git_manager.get_all_markdown_files()

        assert result == []

    def test_get_last_sync_info_no_repo(self):
        """Test getting sync info when repository is not initialized."""
        result = self.git_manager.get_last_sync_info()

        assert result == {}

    def test_get_last_sync_info_success(self):
        """Test successful retrieval of sync info."""
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.committed_date = 1640995200  # 2022-01-01 00:00:00 UTC
        mock_commit.message = "Test commit message\n"

        mock_repo.head.commit = mock_commit
        self.git_manager.repo = mock_repo

        with patch("src.services.git_manager.datetime") as mock_datetime:
            mock_datetime.fromtimestamp.return_value.isoformat.return_value = (
                "2022-01-01T00:00:00"
            )
            result = self.git_manager.get_last_sync_info()

        expected = {
            "commit_hash": "abc123",
            "commit_date": "2022-01-01T00:00:00",
            "commit_message": "Test commit message",
        }

        assert result == expected

    @patch("builtins.print")
    def test_get_last_sync_info_error(self, mock_print):
        """Test getting sync info with error."""
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.committed_date = (
            "not_an_integer"  # This will cause datetime.fromtimestamp to fail
        )
        mock_commit.message = "Test message"

        mock_repo.head.commit = mock_commit
        self.git_manager.repo = mock_repo

        result = self.git_manager.get_last_sync_info()

        assert result == {}
        # The actual error message will contain information about the Mock object
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Failed to get sync info:" in call_args


class TestFileChange:
    """Test cases for FileChange model."""

    def test_file_change_creation(self):
        """Test FileChange model creation."""
        change = FileChange(
            file_path="test.md", change_type="M", old_file_path="old_test.md"
        )

        assert change.file_path == "test.md"
        assert change.change_type == "M"
        assert change.old_file_path == "old_test.md"

    def test_file_change_without_old_path(self):
        """Test FileChange model creation without old file path."""
        change = FileChange(file_path="test.md", change_type="A")

        assert change.file_path == "test.md"
        assert change.change_type == "A"
        assert change.old_file_path is None
