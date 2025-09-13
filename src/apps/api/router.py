from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from src.config.settings import Settings, get_settings
from src.schemas import SearchRequest
from src.services import SyncCoordinator
from src.services.vector_store import VectorStore

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
                github_token=settings.OBS_VAULT_TOKEN,
                embedding_model=settings.EMBEDDING_MODEL_NAME,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize sync coordinator: {str(e)}",
            )
    return _sync_coordinator


@router.post("/sync", response_model=Dict[str, Any])
async def sync_repository(
    full_sync: bool = False,
    coordinator: SyncCoordinator = Depends(get_sync_coordinator),
):
    """Synchronize repository with incremental or full sync."""
    try:
        if full_sync:
            result = coordinator.full_sync()
        else:
            result = coordinator.incremental_sync()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/search", response_model=Dict[str, Any])
async def search_documents(
    request: SearchRequest, coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """Search documents in the vector store."""
    # Validate request
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if request.n_results < 1:
        raise HTTPException(status_code=400, detail="n_results must be positive")

    try:
        results = coordinator.search_documents(
            query=request.query,
            n_results=request.n_results,
            file_filter=request.file_filter,
            tag_filter=request.tag_filter,
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/health")
async def obs_health_check():
    """Simple health check for obs endpoints."""
    return {"status": "obs endpoints available"}


@router.get("/status", response_model=Dict[str, Any])
async def get_status(coordinator: SyncCoordinator = Depends(get_sync_coordinator)):
    """Get repository and vector store status."""
    try:
        return coordinator.get_repository_status()
    except Exception as e:
        return {
            "sync_status": "error",
            "repository": {"status": "error", "error": str(e)},
            "vector_store": {"status": "error", "error": str(e)},
        }


@router.post("/reindex/{file_path:path}", response_model=Dict[str, Any])
async def reindex_file(file_path: str):
    """Force re-indexing of a specific file."""
    return {"status": "reindex would happen", "file_path": file_path}


@router.post("/build-index", response_model=Dict[str, Any])
async def build_index(settings: Settings = Depends(get_settings)):
    """Build or rebuild the entire vector index by cloning if needed and performing full sync."""
    sc = get_sync_coordinator(settings)
    # If repository not set up yet, perform initial setup (clone + full sync)
    if getattr(sc.git_manager, "repo", None) is None:
        result = sc.initial_setup()
        return {"status": "build-index complete", "result": result}
    # Repository exists: update repository, clear existing index and rebuild
    # First update repository to latest (including submodules)
    if not sc.git_manager.pull_changes():
        raise HTTPException(status_code=500, detail="Failed to update repository")

    import shutil
    from pathlib import Path

    db_path = sc.vector_store.persist_directory
    if Path(db_path).exists():
        try:
            shutil.rmtree(db_path)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to clear existing index: {str(e)}"
            )
    # Reinitialize vector store for fresh indexing
    sc.vector_store = VectorStore(
        persist_directory=str(db_path), model_name=settings.EMBEDDING_MODEL_NAME
    )
    # Perform full synchronization
    result = sc.full_sync()
    return {"status": "build-index complete", "result": result}
