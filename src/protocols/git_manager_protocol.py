"""Git Manager protocol interface."""

from pathlib import Path
from typing import Dict, List, Protocol, runtime_checkable

# Import the existing FileChange model
from ..models import FileChange


@runtime_checkable
class GitManagerProtocol(Protocol):
    """Protocol for git repository management operations."""

    @property
    def repo_url(self) -> str:
        """Repository URL."""
        ...

    @property
    def local_path(self) -> Path:
        """Local repository path."""
        ...

    @property
    def branch(self) -> str:
        """Current branch name."""
        ...

    def setup_repository(self) -> bool:
        """Setup repository (clone if needed). Returns True if successful."""
        ...

    def pull_changes(self) -> bool:
        """Pull latest changes from remote. Returns True if successful."""
        ...

    def get_all_markdown_files(self) -> List[str]:
        """Get list of all markdown files in the repository."""
        ...

    def get_file_content(self, file_path: str) -> str:
        """Get content of a specific file."""
        ...

    def get_changed_files(self) -> List[FileChange]:
        """Get list of files changed since last sync."""
        ...

    def get_last_sync_info(self) -> Dict[str, str]:
        """Get information about the last sync (commit hash, date, etc)."""
        ...
