"""Services for the application."""

from .git_manager_factory import (
    create_git_manager,
    create_git_manager_from_settings,
)
from .sync_coordinator import SyncCoordinator

__all__ = [
    "SyncCoordinator",
    "create_git_manager",
    "create_git_manager_from_settings",
]
