"""Factory for creating GitManager instances with DEBUG mode support."""

from ..config.settings import Settings
from ..models import GitManager
from ..protocols.git_manager_protocol import GitManagerProtocol


def create_git_manager(
    repo_url: str,
    local_path: str,
    branch: str = "main",
    github_token: str = "",
    debug_mode: bool = False,
) -> GitManagerProtocol:
    """
    Create a GitManager instance based on debug mode.

    Args:
        repo_url: Repository URL
        local_path: Local repository path
        branch: Git branch name
        github_token: GitHub personal access token
        debug_mode: If True, returns MockGitManager; if False, returns real GitManager

    Returns:
        GitManagerProtocol implementation
    """
    if debug_mode:
        print("🔧 DEBUG mode: Using MockGitManager")
        # Lazy import to avoid import issues when dev path isn't set up yet
        try:
            from mocks.git_manager import MockGitManager

            return MockGitManager(repo_url, local_path, branch, github_token)
        except ImportError:
            print("⚠️  MockGitManager not available, falling back to real GitManager")
            return GitManager(repo_url, local_path, branch, github_token)
    else:
        print("🌐 Production mode: Using real GitManager")
        return GitManager(repo_url, local_path, branch, github_token)


def create_git_manager_from_settings(settings: Settings) -> GitManagerProtocol:
    """
    Create a GitManager instance using application settings.

    Args:
        settings: Application settings

    Returns:
        GitManagerProtocol implementation
    """
    return create_git_manager(
        repo_url=settings.OBSIDIAN_REPO_URL,
        local_path=settings.OBSIDIAN_LOCAL_PATH,
        branch=settings.OBSIDIAN_BRANCH,
        github_token=settings.OBS_VAULT_TOKEN,
        debug_mode=settings.DEBUG,
    )
