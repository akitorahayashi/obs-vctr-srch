import asyncio
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.config.settings import Settings
from src.dependencies import get_settings, get_sync_coordinator
from src.schemas import SearchRequest
from src.services import SyncCoordinator

router = APIRouter(prefix="/obs-vctr-srch", tags=["obs-vctr-srch"])


@router.post("/sync", response_model=Dict[str, Any])
async def sync_repository(
    coordinator: SyncCoordinator = Depends(get_sync_coordinator),
):
    """Synchronize repository with incremental sync."""
    try:
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
async def build_index(
    coordinator: SyncCoordinator = Depends(get_sync_coordinator),
    settings: Settings = Depends(get_settings),
):
    """Build or rebuild the entire vector index."""

    def _build_index_sync():
        return coordinator.rebuild_index()

    try:
        # Run with configurable timeout
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _build_index_sync),
            timeout=float(settings.BUILD_INDEX_TIMEOUT),
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail=f"Build index operation timed out after {settings.BUILD_INDEX_TIMEOUT} seconds",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build index failed: {str(e)}")


@router.post("/build-index-stream")
async def build_index_stream(
    coordinator: SyncCoordinator = Depends(get_sync_coordinator),
):
    """Build or rebuild the entire vector index with streaming progress updates."""

    async def generate_progress():
        async for progress in coordinator.rebuild_index_stream():
            yield f"data: {json.dumps(progress)}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
