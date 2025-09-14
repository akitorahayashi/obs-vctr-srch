import asyncio
import json
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.config.settings import Settings, get_settings
from src.services.sync_coordinator import SyncCoordinator
from src.services.vector_store import SearchRequest, VectorStore

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
                debug_mode=settings.DEBUG,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize sync coordinator: {str(e)}",
            )
    return _sync_coordinator


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
async def build_index(settings: Settings = Depends(get_settings)):
    """Build or rebuild the entire vector index by cloning if needed and performing full sync."""

    def _build_index_sync():
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
async def build_index_stream(settings: Settings = Depends(get_settings)):
    """Build or rebuild the entire vector index with streaming progress updates."""

    async def generate_progress():
        try:
            sc = get_sync_coordinator(settings)

            # Initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting build index process...', 'progress': 0})}\n\n"

            # Setup repository if needed
            if getattr(sc.git_manager, "repo", None) is None:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Setting up repository...', 'progress': 5})}\n\n"
                if not sc.git_manager.setup_repository():
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to setup repository'})}\n\n"
                    return
            else:
                # Update repository
                yield f"data: {json.dumps({'type': 'status', 'message': 'Updating repository...', 'progress': 5})}\n\n"
                if not sc.git_manager.pull_changes():
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to update repository'})}\n\n"
                    return

            # Clear existing index
            yield f"data: {json.dumps({'type': 'status', 'message': 'Clearing existing index...', 'progress': 10})}\n\n"

            import shutil
            from pathlib import Path

            db_path = sc.vector_store.persist_directory
            if Path(db_path).exists():
                try:
                    shutil.rmtree(db_path)
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to clear existing index: {str(e)}'})}\n\n"
                    return

            # Reinitialize vector store
            from src.services.vector_store import VectorStore

            sc.vector_store = VectorStore(
                persist_directory=str(db_path), model_name=settings.EMBEDDING_MODEL_NAME
            )

            # Get all files to process
            yield f"data: {json.dumps({'type': 'status', 'message': 'Scanning markdown files...', 'progress': 15})}\n\n"
            md_files = sc.git_manager.get_all_markdown_files()

            if not md_files:
                yield f"data: {json.dumps({'type': 'complete', 'message': 'No markdown files found', 'stats': {'processed': 0, 'failed': 0}})}\n\n"
                return

            total_files = len(md_files)
            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {total_files} files to process', 'progress': 20, 'total_files': total_files})}\n\n"

            # Process files with streaming progress
            stats = {"processed": 0, "failed": 0, "total_chunks": 0}
            start_time = time.time()

            for i, file_path in enumerate(md_files):
                try:
                    # Calculate progress (20% to 90% for file processing)
                    progress = 20 + (i / total_files) * 70

                    # Calculate estimated completion time
                    if i > 0:
                        elapsed = time.time() - start_time
                        avg_time_per_file = elapsed / i
                        remaining_files = total_files - i
                        eta_seconds = remaining_files * avg_time_per_file
                        eta_minutes = int(eta_seconds / 60)
                        eta_seconds = int(eta_seconds % 60)
                        eta_str = f"{eta_minutes}m {eta_seconds}s"
                    else:
                        eta_str = "calculating..."

                    yield f"data: {json.dumps({'type': 'progress', 'message': f'Processing: {file_path}', 'progress': progress, 'current_file': i + 1, 'total_files': total_files, 'eta': eta_str})}\n\n"

                    # Get file content
                    content = sc.git_manager.get_file_content(file_path)
                    if not content:
                        stats["failed"] += 1
                        yield f"data: {json.dumps({'type': 'warning', 'message': f'No content found for: {file_path}'})}\n\n"
                        continue

                    # Process the file
                    document = sc.processor.process_file(file_path, content)
                    if not document:
                        stats["failed"] += 1
                        yield f"data: {json.dumps({'type': 'warning', 'message': f'Failed to process: {file_path}'})}\n\n"
                        continue

                    # Split into chunks for embedding
                    chunks = sc.processor.split_content_for_embedding(document)

                    # Add to vector store
                    if sc.vector_store.add_document(document, chunks):
                        stats["processed"] += 1
                        stats["total_chunks"] += len(chunks)
                        yield f"data: {json.dumps({'type': 'file_complete', 'message': f'✅ Processed: {file_path} ({len(chunks)} chunks)', 'file_path': file_path, 'chunks': len(chunks)})}\n\n"
                    else:
                        stats["failed"] += 1
                        yield f"data: {json.dumps({'type': 'warning', 'message': f'Failed to add to vector store: {file_path}'})}\n\n"

                except Exception as e:
                    stats["failed"] += 1
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Error processing {file_path}: {str(e)}'})}\n\n"

            # Final completion
            total_time = time.time() - start_time
            yield f"data: {json.dumps({'type': 'status', 'message': 'Finalizing...', 'progress': 95})}\n\n"

            result = {
                "type": "complete",
                "message": f'Build index complete! Processed {stats["processed"]} files, {stats["failed"]} failed',
                "stats": stats,
                "total_time_seconds": round(total_time, 2),
                "progress": 100,
            }
            yield f"data: {json.dumps(result)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Build index failed: {str(e)}'})}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    )
