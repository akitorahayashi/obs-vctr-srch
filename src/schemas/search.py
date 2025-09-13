from typing import List, Optional

from pydantic import BaseModel


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
