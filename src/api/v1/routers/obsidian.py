from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from src.config.settings import Settings, get_settings
from src.services.sync_coordinator import SyncCoordinator

router = APIRouter(prefix="/obsidian", tags=["obsidian"])

# Global sync coordinator instance
_sync_coordinator: Optional[SyncCoordinator] = None


def get_sync_coordinator(settings: Settings = Depends(get_settings)) -> SyncCoordinator:
    """Get or create sync coordinator instance."""
    global _sync_coordinator
    if _sync_coordinator is None:
        _sync_coordinator = SyncCoordinator(
            repo_url=settings.OBSIDIAN_REPO_URL,
            local_path=settings.OBSIDIAN_LOCAL_PATH,
            vector_store_path=settings.VECTOR_DB_PATH,
            branch=settings.OBSIDIAN_BRANCH,
            github_token=settings.GITHUB_TOKEN,
        )
    return _sync_coordinator


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


@router.post("/setup", response_model=Dict[str, Any])
async def setup_repository(
    background_tasks: BackgroundTasks,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
):
    """Initialize repository and perform initial synchronization."""
    try:
        result = sync_coordinator.initial_setup()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=Dict[str, Any])
async def sync_repository(
    full_sync: bool = False,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
):
    """Synchronize repository with incremental or full sync."""
    try:
        if full_sync:
            result = sync_coordinator.full_sync()
        else:
            result = sync_coordinator.incremental_sync()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=List[SearchResult])
async def search_documents(
    request: SearchRequest,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
):
    """Search documents in the vector store."""
    try:
        results = sync_coordinator.search_documents(
            query=request.query,
            n_results=request.n_results,
            file_filter=request.file_filter,
            tag_filter=request.tag_filter,
        )

        return [
            SearchResult(
                id=result["id"],
                content=result["content"],
                distance=result["distance"],
                file_path=result["file_path"],
                title=result["title"],
                chunk_index=result["chunk_index"],
                tags=result["tags"],
                links=result["links"],
                created_at=result["created_at"],
                modified_at=result["modified_at"],
            )
            for result in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=Dict[str, Any])
async def get_status(sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)):
    """Get repository and vector store status."""
    try:
        status = sync_coordinator.get_repository_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", response_model=Dict[str, Any])
async def cleanup_orphaned_embeddings(
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
):
    """Remove embeddings for files that no longer exist."""
    try:
        result = sync_coordinator.cleanup_orphaned_embeddings()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex/{file_path:path}", response_model=Dict[str, Any])
async def reindex_file(
    file_path: str, sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """Force re-indexing of a specific file."""
    try:
        result = sync_coordinator.force_reindex_file(file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict[str, Any])
async def get_vector_store_stats(
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
):
    """Get detailed vector store statistics."""
    try:
        stats = sync_coordinator.vector_store.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
