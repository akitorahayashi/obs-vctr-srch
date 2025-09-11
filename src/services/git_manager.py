from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from git import Repo
from pydantic import BaseModel


class FileChange(BaseModel):
    """Represents a file change detected by git diff."""

    file_path: str
    change_type: str  # 'A' (added), 'M' (modified), 'D' (deleted), 'R' (renamed)
    old_file_path: Optional[str] = None  # For renamed files


class GitManager:
    """Manages git repository operations for Obsidian vault."""

    def __init__(
        self,
        repo_url: str,
        local_path: str,
        branch: str = "main",
        github_token: str = "",
    ):
        self.repo_url = repo_url
        self.local_path = Path(local_path)
        self.branch = branch
        self.github_token = github_token
        self.repo: Optional[Repo] = None

    def setup_repository(self) -> bool:
        """Clone or initialize the repository."""
        try:
            if self.local_path.exists() and (self.local_path / ".git").exists():
                # Repository already exists, just open it
                self.repo = Repo(self.local_path)
                print(f"Repository already exists at {self.local_path}")
                return True
            else:
                # Build clone URL with token for private repos
                clone_url = self._build_clone_url()

                # Clone the repository
                print(f"Cloning repository from {self.repo_url}")
                self.repo = Repo.clone_from(
                    clone_url, self.local_path, branch=self.branch
                )
                print(f"Repository cloned to {self.local_path}")
                return True
        except Exception as e:
            print(f"Failed to setup repository: {e}")
            return False

    def _build_clone_url(self) -> str:
        """Build clone URL with token for private repositories."""
        if self.github_token and "github.com" in self.repo_url:
            # Extract repo info from URL
            repo_part = self.repo_url.replace("https://github.com/", "")
            return f"https://{self.github_token}@github.com/{repo_part}"
        return self.repo_url

    def get_changed_files(self) -> List[FileChange]:
        """Get list of changed files since last sync."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")

        try:
            # Fetch latest changes
            origin = self.repo.remotes.origin
            origin.fetch()

            # Get current HEAD and origin HEAD
            local_commit = self.repo.head.commit
            remote_commit = origin.refs[self.branch].commit

            if local_commit.hexsha == remote_commit.hexsha:
                print("No changes detected")
                return []

            # Get diff between local and remote
            diff_items = local_commit.diff(remote_commit)

            changes = []
            for item in diff_items:
                change_type = item.change_type
                file_path = item.a_path or item.b_path
                old_file_path = item.a_path if item.renamed_file else None

                # Only process .md files (Obsidian notes)
                if file_path and file_path.endswith(".md"):
                    changes.append(
                        FileChange(
                            file_path=file_path,
                            change_type=change_type,
                            old_file_path=old_file_path,
                        )
                    )

            return changes

        except Exception as e:
            print(f"Failed to get changed files: {e}")
            return []

    def pull_changes(self) -> bool:
        """Pull latest changes from remote."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")

        try:
            origin = self.repo.remotes.origin
            origin.pull()
            print("Successfully pulled latest changes")
            return True
        except Exception as e:
            print(f"Failed to pull changes: {e}")
            return False

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get content of a specific file."""
        try:
            full_path = self.local_path / file_path
            if full_path.exists():
                return full_path.read_text(encoding="utf-8")
            return None
        except Exception as e:
            print(f"Failed to read file {file_path}: {e}")
            return None

    def get_all_markdown_files(self) -> List[str]:
        """Get list of all markdown files in the repository."""
        if not self.local_path.exists():
            return []

        md_files = []
        for file_path in self.local_path.rglob("*.md"):
            relative_path = file_path.relative_to(self.local_path)
            md_files.append(str(relative_path))

        return md_files

    def get_last_sync_info(self) -> Dict[str, str]:
        """Get information about the last sync."""
        if not self.repo:
            return {}

        try:
            last_commit = self.repo.head.commit
            return {
                "commit_hash": last_commit.hexsha,
                "commit_date": datetime.fromtimestamp(
                    last_commit.committed_date
                ).isoformat(),
                "commit_message": last_commit.message.strip(),
            }
        except Exception as e:
            print(f"Failed to get sync info: {e}")
            return {}
