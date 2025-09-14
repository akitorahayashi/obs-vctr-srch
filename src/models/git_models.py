"""Git-related model classes."""

from typing import Optional

from pydantic import BaseModel


class FileChange(BaseModel):
    """Represents a file change detected by git diff."""

    file_path: str
    change_type: str  # 'A' (added), 'M' (modified), 'D' (deleted), 'R' (renamed)
    old_file_path: Optional[str] = None  # For renamed files
