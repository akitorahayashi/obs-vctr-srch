"""Coordinates synchronization between Git repository and vector store."""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.models import GitManager, ObsidianProcessor, VectorStore
from src.schemas import FileStatus


class SyncCoordinator:
    """Coordinates synchronization between git repo and vector embeddings."""

    def __init__(
        self,
        git_manager: GitManager,
        vector_store: VectorStore,
        processor: ObsidianProcessor,
    ):
        self.git_manager = git_manager
        self.vector_store = vector_store
        self.processor = processor

    async def rebuild_index_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Rebuild the entire vector index with streaming progress updates."""
        try:
            yield {
                "type": "status",
                "message": "Starting build index process...",
                "progress": 0,
            }

            if getattr(self.git_manager, "repo", None) is None:
                yield {
                    "type": "status",
                    "message": "Setting up repository...",
                    "progress": 5,
                }
                if not self.git_manager.setup_repository():
                    yield {"type": "error", "message": "Failed to setup repository"}
                    return
            else:
                yield {
                    "type": "status",
                    "message": "Updating repository...",
                    "progress": 5,
                }
                if not self.git_manager.pull_changes():
                    yield {"type": "error", "message": "Failed to update repository"}
                    return

            yield {
                "type": "status",
                "message": "Clearing existing index...",
                "progress": 10,
            }
            clear_result = await asyncio.to_thread(self.vector_store.clear_collection)
            if not clear_result["success"]:
                yield {
                    "type": "error",
                    "message": f"Failed to clear existing index: {clear_result['message']}",
                }
                return

            yield {
                "type": "status",
                "message": "Scanning markdown files...",
                "progress": 15,
            }
            md_files = await asyncio.to_thread(self.git_manager.get_all_markdown_files)

            if not md_files:
                yield {
                    "type": "complete",
                    "message": "No markdown files found",
                    "stats": {"processed": 0, "failed": 0},
                }
                return

            total_files = len(md_files)
            yield {
                "type": "status",
                "message": f"Found {total_files} files to process",
                "progress": 20,
                "total_files": total_files,
            }

            stats = {"processed": 0, "failed": 0, "total_chunks": 0}
            start_time = time.time()

            for i, file_path in enumerate(md_files):
                progress = 20 + (i / total_files) * 70
                if i > 0:
                    elapsed = time.time() - start_time
                    avg_time_per_file = elapsed / i
                    remaining_files = total_files - i
                    eta_seconds = remaining_files * avg_time_per_file
                    eta_str = f"{int(eta_seconds / 60)}m {int(eta_seconds % 60)}s"
                else:
                    eta_str = "calculating..."

                yield {
                    "type": "progress",
                    "message": f"Processing: {file_path}",
                    "progress": progress,
                    "current_file": i + 1,
                    "total_files": total_files,
                    "eta": eta_str,
                }

                try:
                    content = await asyncio.to_thread(
                        self.git_manager.get_file_content, file_path
                    )
                    if content is None:
                        stats["failed"] += 1
                        yield {
                            "type": "warning",
                            "message": f"No content found for: {file_path}",
                        }
                        continue

                    document = await asyncio.to_thread(
                        self.processor.process_file, file_path, content
                    )
                    if not document:
                        stats["failed"] += 1
                        yield {
                            "type": "warning",
                            "message": f"Failed to process: {file_path}",
                        }
                        continue

                    chunks = await asyncio.to_thread(
                        self.processor.split_content_for_embedding, document
                    )
                    ok = await asyncio.to_thread(
                        self.vector_store.add_document, document, chunks
                    )
                    if ok:
                        stats["processed"] += 1
                        stats["total_chunks"] += len(chunks)
                        yield {
                            "type": "file_complete",
                            "message": f"✅ Processed: {file_path} ({len(chunks)} chunks)",
                            "file_path": file_path,
                            "chunks": len(chunks),
                        }
                    else:
                        stats["failed"] += 1
                        yield {
                            "type": "warning",
                            "message": f"Failed to add to vector store: {file_path}",
                        }

                except Exception as e:
                    stats["failed"] += 1
                    yield {
                        "type": "error",
                        "message": f"Error processing {file_path}: {str(e)}",
                    }

            total_time = time.time() - start_time
            yield {"type": "status", "message": "Finalizing...", "progress": 95}

            result = {
                "type": "complete",
                "message": f'Build index complete! Processed {stats["processed"]} files, {stats["failed"]} failed',
                "stats": stats,
                "total_time_seconds": round(total_time, 2),
                "progress": 100,
            }
            yield result

        except Exception as e:  # noqa: BLE001 - stream safety
            yield {"type": "error", "message": f"Build index failed: {str(e)}"}

    async def incremental_sync_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Perform incremental synchronization with streaming progress updates."""
        try:
            yield {
                "type": "status",
                "message": "Starting incremental sync...",
                "progress": 0,
            }

            # Get changed files
            yield {
                "type": "status",
                "message": "Detecting file changes...",
                "progress": 10,
            }
            changes = self.git_manager.get_changed_files()

            if not changes:
                yield {
                    "type": "complete",
                    "message": "No changes detected - sync up to date",
                    "stats": {"processed": 0, "deleted": 0, "renamed": 0, "failed": 0},
                }
                return

            yield {
                "type": "status",
                "message": f"Found {len(changes)} file changes",
                "progress": 20,
                "total_changes": len(changes),
            }

            # Process file changes in vector store (deletions and renames)
            yield {
                "type": "status",
                "message": "Processing deletions and renames...",
                "progress": 25,
            }
            change_stats = self.vector_store.process_file_changes(changes)

            # Pull the latest changes
            yield {
                "type": "status",
                "message": "Pulling latest changes from repository...",
                "progress": 30,
            }
            if not self.git_manager.pull_changes():
                yield {"type": "error", "message": "Failed to pull changes"}
                return

            # Process added/modified files
            stats = {
                "processed": 0,
                "failed": 0,
                "total_chunks": 0,
                "deleted": change_stats.get("deleted", 0),
                "renamed": change_stats.get("renamed", 0),
            }

            # Filter for added/modified files that need processing
            files_to_process = [
                change
                for change in changes
                if change.status in [FileStatus.ADDED, FileStatus.MODIFIED]
            ]

            if not files_to_process:
                yield {
                    "type": "complete",
                    "message": "Sync complete - only deletions/renames processed",
                    "stats": stats,
                }
                return

            total_files = len(files_to_process)
            start_time = time.time()

            yield {
                "type": "status",
                "message": f"Processing {total_files} added/modified files...",
                "progress": 35,
                "total_files": total_files,
            }

            for i, change in enumerate(files_to_process):
                progress = 35 + (i / total_files) * 60

                # Calculate ETA
                if i > 0:
                    elapsed = time.time() - start_time
                    avg_time_per_file = elapsed / i
                    remaining_files = total_files - i
                    eta_seconds = remaining_files * avg_time_per_file
                    eta_str = f"{int(eta_seconds / 60)}m {int(eta_seconds % 60)}s"
                else:
                    eta_str = "calculating..."

                yield {
                    "type": "progress",
                    "message": f"Processing: {change.file_path}",
                    "progress": progress,
                    "current_file": i + 1,
                    "total_files": total_files,
                    "eta": eta_str,
                }

                try:
                    # Get file content
                    content = await asyncio.to_thread(
                        self.git_manager.get_file_content, change.file_path
                    )
                    if content is None:
                        stats["failed"] += 1
                        yield {
                            "type": "warning",
                            "message": f"No content found for: {change.file_path}",
                        }
                        continue

                    # Process the file
                    document = await asyncio.to_thread(
                        self.processor.process_file, change.file_path, content
                    )
                    if not document:
                        stats["failed"] += 1
                        yield {
                            "type": "warning",
                            "message": f"Failed to process: {change.file_path}",
                        }
                        continue

                    # Split into chunks for embedding
                    chunks = await asyncio.to_thread(
                        self.processor.split_content_for_embedding, document
                    )

                    # Add to vector store
                    ok = await asyncio.to_thread(
                        self.vector_store.add_document, document, chunks
                    )
                    if ok:
                        stats["processed"] += 1
                        stats["total_chunks"] += len(chunks)
                        yield {
                            "type": "file_complete",
                            "message": f"✅ Synced: {change.file_path} ({len(chunks)} chunks)",
                            "file_path": change.file_path,
                            "chunks": len(chunks),
                            "status": change.status.value,
                        }
                    else:
                        stats["failed"] += 1
                        yield {
                            "type": "warning",
                            "message": f"Failed to add to vector store: {change.file_path}",
                        }

                except Exception as e:
                    stats["failed"] += 1
                    yield {
                        "type": "error",
                        "message": f"Error processing {change.file_path}: {str(e)}",
                    }

            total_time = time.time() - start_time
            yield {"type": "status", "message": "Finalizing sync...", "progress": 95}

            result = {
                "type": "complete",
                "message": f'Incremental sync complete! Processed {stats["processed"]} files, {stats["failed"]} failed, {stats["deleted"]} deleted, {stats["renamed"]} renamed',
                "stats": stats,
                "total_time_seconds": round(total_time, 2),
                "progress": 100,
            }
            yield result

        except Exception as e:  # noqa: BLE001 - stream safety
            yield {"type": "error", "message": f"Incremental sync failed: {str(e)}"}

    def search_documents(
        self,
        query: str,
        n_results: int = 10,
        file_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Search documents in the vector store."""
        return self.vector_store.search(
            query=query,
            n_results=n_results,
            file_filter=file_filter,
            tag_filter=tag_filter,
        )

    async def get_repository_status(self) -> Dict[str, Any]:
        """Get current repository and vector store status."""
        try:
            # Git status
            sync_info = await asyncio.to_thread(self.git_manager.get_last_sync_info)

            # Vector store stats
            vector_stats = await asyncio.to_thread(self.vector_store.get_stats)

            # Repository info
            repo_files = await asyncio.to_thread(
                self.git_manager.get_all_markdown_files
            )

            repository_info = {
                "url": self.git_manager.repo_url,
                "local_path": str(self.git_manager.local_path),
                "branch": self.git_manager.branch,
                "total_md_files": len(repo_files),
                "status": "available",
            }

            # Add commit info directly to repository level if available
            if sync_info and "commit_hash" in sync_info:
                repository_info["commit_hash"] = sync_info["commit_hash"]
                repository_info["last_sync"] = sync_info["commit_date"]

            return {
                "repository": repository_info,
                "vector_store": vector_stats,
                "sync_status": "ready",
            }

        except Exception as e:
            return {
                "repository": {"status": "error", "error": str(e)},
                "vector_store": {"status": "error", "error": str(e)},
                "sync_status": "error",
                "error": str(e),
            }

    async def cleanup_orphaned_embeddings(self) -> Dict[str, int]:
        """Remove embeddings for files that no longer exist in the repository."""
        try:
            # Get all files in vector store
            stored_files = set(
                await asyncio.to_thread(self.vector_store.list_all_documents)
            )

            # Get all files in repository
            repo_files = set(
                await asyncio.to_thread(self.git_manager.get_all_markdown_files)
            )

            # Find orphaned files
            orphaned_files = stored_files - repo_files

            if not orphaned_files:
                return {"removed": 0, "message": "No orphaned embeddings found"}

            # Remove orphaned embeddings
            removed_count = 0
            for file_path in orphaned_files:
                removed = await asyncio.to_thread(
                    self.vector_store.remove_document, file_path
                )
                if removed:
                    removed_count += 1

            return {
                "removed": removed_count,
                "total_orphaned": len(orphaned_files),
                "message": f"Removed {removed_count} orphaned embeddings",
            }

        except Exception as e:
            return {"error": str(e)}
