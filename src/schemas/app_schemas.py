"""Application-wide schema classes."""

from typing import List, Optional

from pydantic import BaseModel


class FileChange(BaseModel):
    """Represents a file change detected by git diff."""

    file_path: str
    change_type: str  # 'A' (added), 'M' (modified), 'D' (deleted), 'R' (renamed)
    old_file_path: Optional[str] = None  # For renamed files


class SearchRequest(BaseModel):
    query: str
    n_results: int = 10
    file_filter: Optional[str] = None
    tag_filter: Optional[List[str]] = None


class SearchResult(BaseModel):
    id: str
    content: str
    distance: float
    file_path: str
    title: str
    chunk_index: int
    tags: List[str]
    links: List[str]
    created_at: Optional[str]
    modified_at: Optional[str]
