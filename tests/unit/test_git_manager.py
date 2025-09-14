"""Unit tests for GitManager class."""

from pathlib import Path
from unittest.mock import Mock, patch

from src.config.settings import Settings
from src.models import GitManager
from src.schemas import FileChange, FileStatus


class TestGitManager:
    """Test cases for GitManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Mock(spec=Settings)
        self.settings.OBSIDIAN_REPO_URL = "https://github.com/test/repo.git"
        self.settings.OBSIDIAN_LOCAL_PATH = "/tmp/test_repo"
        self.settings.OBSIDIAN_BRANCH = "main"
        self.settings.OBS_VAULT_TOKEN = "test_token"
        self.git_manager = GitManager(self.settings)

    def test_init(self):
        """Test GitManager initialization."""
        assert self.git_manager.repo_url == self.settings.OBSIDIAN_REPO_URL
        assert self.git_manager.local_path == Path(self.settings.OBSIDIAN_LOCAL_PATH)
        assert self.git_manager.branch == self.settings.OBSIDIAN_BRANCH
        assert self.git_manager.github_token == self.settings.OBS_VAULT_TOKEN
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
        assert result == self.settings.OBSIDIAN_REPO_URL

    @patch("src.models.git_manager.Repo")
    @patch("pathlib.Path.exists")
    def test_setup_repository_existing_repo(self, mock_exists, mock_repo_class):
        """Test setup when repository already exists."""
        mock_exists.return_value = True
        mock_repo = Mock()
        mock_repo.submodules = []
        mock_repo_class.return_value = mock_repo

        result = self.git_manager.setup_repository()

        assert result is True
        assert self.git_manager.repo == mock_repo
        mock_repo_class.assert_called_once_with(self.git_manager.local_path)

    @patch("src.models.git_manager.Repo")
    @patch("pathlib.Path.exists")
    def test_setup_repository_clone_new(self, mock_exists, mock_repo_class):
        """Test setup when cloning new repository."""
        mock_exists.return_value = False
        mock_repo = Mock()
        mock_repo.submodules = []
        mock_repo_class.clone_from.return_value = mock_repo

        result = self.git_manager.setup_repository()

        assert result is True
        assert self.git_manager.repo == mock_repo
        mock_repo_class.clone_from.assert_called_once_with(
            "https://test_token@github.com/test/repo.git",
            self.git_manager.local_path,
            branch=self.settings.OBSIDIAN_BRANCH,
        )

    def test_get_changed_files_with_changes(self):
        """Test getting changed files when changes exist."""
        mock_repo = Mock()
        mock_origin = Mock()
        mock_local_commit = Mock()
        mock_remote_commit = Mock()
        mock_local_commit.hexsha = "abc123"
        mock_remote_commit.hexsha = "def456"
        mock_origin.refs = {"main": Mock(commit=mock_remote_commit)}
        mock_repo.remotes.origin = mock_origin
        mock_repo.head.commit = mock_local_commit

        mock_diff_item1 = Mock(
            change_type="M", a_path="test1.md", b_path="test1.md", renamed=False
        )
        mock_diff_item2 = Mock(
            change_type="A", a_path=None, b_path="test2.md", renamed=False
        )
        mock_diff_item3 = Mock(
            change_type="M", a_path="test3.py", b_path="test3.py", renamed=False
        )
        mock_local_commit.diff.return_value = [
            mock_diff_item1,
            mock_diff_item2,
            mock_diff_item3,
        ]
        self.git_manager.repo = mock_repo

        result = self.git_manager.get_changed_files()

        assert len(result) == 2
        assert result[0].file_path == "test1.md"
        assert result[0].status == FileStatus.MODIFIED
        assert result[1].file_path == "test2.md"
        assert result[1].status == FileStatus.ADDED


class TestFileChange:
    """Test cases for FileChange model."""

    def test_file_change_creation(self):
        """Test FileChange model creation."""
        change = FileChange(
            file_path="test.md", status=FileStatus.RENAMED, old_file_path="old_test.md"
        )

        assert change.file_path == "test.md"
        assert change.status == FileStatus.RENAMED
        assert change.old_file_path == "old_test.md"

    def test_file_change_without_old_path(self):
        """Test FileChange model creation without old file path."""
        change = FileChange(file_path="test.md", status=FileStatus.ADDED)

        assert change.file_path == "test.md"
        assert change.status == FileStatus.ADDED
        assert change.old_file_path is None
