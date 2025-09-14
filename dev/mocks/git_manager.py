"""Mock implementation of GitManagerProtocol for development and testing."""

# Import the existing FileChange model
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.models import FileChange


class MockGitManager:
    """Mock implementation of GitManagerProtocol that uses local filesystem."""

    def __init__(
        self,
        repo_url: str,
        local_path: str,
        branch: str = "main",
        github_token: str = "",
    ):
        self._repo_url = repo_url
        self._local_path = Path(local_path)
        self._branch = branch
        self._github_token = github_token

        # Use absolute path to dev/mock-vault for all operations
        self._mock_vault_path = Path(__file__).parent.parent / "mock-vault"

        # Track changes for incremental sync simulation
        self._last_sync_time = None
        self._file_modifications = {}

    @property
    def repo_url(self) -> str:
        return self._repo_url

    @property
    def local_path(self) -> Path:
        return self._local_path

    @property
    def branch(self) -> str:
        return self._branch

    def setup_repository(self) -> bool:
        """Mock repository setup - always successful."""
        print(f"Mock: Setting up repository at {self._local_path}")

        # Ensure mock vault exists
        if not self._mock_vault_path.exists():
            print(f"Warning: Mock vault not found at {self._mock_vault_path}")
            return False

        # Create local path if it doesn't exist
        self._local_path.mkdir(parents=True, exist_ok=True)

        print("Mock: Repository setup completed")
        return True

    def pull_changes(self) -> bool:
        """Mock pull operation - always successful."""
        print("Mock: Pulling changes from remote")
        return True

    def get_all_markdown_files(self) -> List[str]:
        """Get all markdown files from mock vault."""
        if not self._mock_vault_path.exists():
            return []

        md_files = []
        for file_path in self._mock_vault_path.rglob("*.md"):
            relative_path = file_path.relative_to(self._mock_vault_path)
            md_files.append(str(relative_path))

        return md_files

    def get_file_content(self, file_path: str) -> str:
        """Get file content from mock vault."""
        full_path = self._mock_vault_path / file_path
        if not full_path.exists():
            return ""

        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Mock: Failed to read {file_path}: {e}")
            return ""

    def get_changed_files(self) -> List[FileChange]:
        """Mock implementation - returns empty list (no changes detected)."""
        print("Mock: Checking for changed files")
        # For simplicity, return no changes in mock mode
        return []

    def get_last_sync_info(self) -> Dict[str, str]:
        """Mock sync info."""
        return {
            "commit_hash": "mock-commit-hash-12345",
            "commit_date": datetime.now().isoformat(),
            "branch": self._branch,
            "status": "mock-synced",
        }
