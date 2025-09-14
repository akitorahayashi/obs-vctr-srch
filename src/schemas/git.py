from enum import Enum
from typing import Optional

from pydantic import BaseModel


class FileStatus(str, Enum):
    """Enum for file change statuses."""

    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"


class FileChange(BaseModel):
    """Represents a file change detected by git diff."""

    status: FileStatus
    file_path: str
    old_file_path: Optional[str] = None  # For renamed files
