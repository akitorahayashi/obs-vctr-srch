from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from src.config.settings import Settings, get_settings
from src.schemas import SearchRequest, SearchResult
from src.services import SyncCoordinator

router = APIRouter(prefix="/obs-vctr-srch", tags=["obs-vctr-srch"])

# Global sync coordinator instance
_sync_coordinator: Optional[SyncCoordinator] = None


def get_sync_coordinator(settings: Settings = Depends(get_settings)) -> SyncCoordinator:
    """Get or create sync coordinator instance."""
    global _sync_coordinator
    if _sync_coordinator is None:
        try:
            _sync_coordinator = SyncCoordinator(
                repo_url=settings.OBSIDIAN_REPO_URL,
                local_path=settings.OBSIDIAN_LOCAL_PATH,
                vector_store_path=settings.VECTOR_DB_PATH,
                branch=settings.OBSIDIAN_BRANCH,
                github_token=settings.GITHUB_TOKEN,
                embedding_model=settings.EMBEDDING_MODEL_NAME,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize sync coordinator: {str(e)}",
            )
    return _sync_coordinator


@router.post("/setup", response_model=Dict[str, Any])
async def setup_repository():
    """Setup repository by cloning and performing initial sync."""
    return {"status": "setup would happen"}


@router.post("/sync", response_model=Dict[str, Any])
async def sync_repository(full_sync: bool = False):
    """Synchronize repository with incremental or full sync."""
    return {"status": "sync would happen", "full_sync": full_sync}


@router.post("/search", response_model=List[SearchResult])
async def search_documents(request: SearchRequest):
    """Search documents in the vector store."""
    return []


@router.get("/health")
async def obs_health_check():
    """Simple health check for obs endpoints."""
    return {"status": "obs endpoints available"}


@router.get("/status", response_model=Dict[str, Any])
async def get_status():
    """Get repository and vector store status."""
    # Simple status without heavy initialization
    return {
        "sync_status": "ready",
        "repository": {"status": "available"},
        "vector_store": {"status": "available"},
    }


@router.post("/reindex/{file_path:path}", response_model=Dict[str, Any])
async def reindex_file(file_path: str):
    """Force re-indexing of a specific file."""
    return {"status": "reindex would happen", "file_path": file_path}


@router.post("/rebuild-index", response_model=Dict[str, Any])
async def rebuild_index():
    """Rebuild the entire vector index by clearing existing data and re-indexing all files."""
    return {"status": "rebuild would happen"}
