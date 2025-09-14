from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import get_sync_coordinator
from src.schemas import SearchRequest
from src.services import SyncCoordinator

router = APIRouter(prefix="/obs-vctr-srch", tags=["obs-vctr-srch"])


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
