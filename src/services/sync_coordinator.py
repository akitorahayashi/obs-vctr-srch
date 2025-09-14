"""Coordinates synchronization between Git repository and vector store."""

import time
from typing import AsyncGenerator, Dict, List, Optional

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

    def initial_setup(self) -> Dict[str, any]:
        """Perform initial repository setup and full sync."""
        print("Starting initial setup...")

        # Setup repository
        if not self.git_manager.setup_repository():
            return {"success": False, "error": "Failed to setup repository"}

        # Perform full sync
        return self.full_sync()

    def full_sync(self) -> Dict[str, any]:
        """Perform a full synchronization of all files."""
        print("Starting full synchronization...")

        try:
            # Get all markdown files from git manager (works with both real and mock)
            md_files = self.git_manager.get_all_markdown_files()

            if not md_files:
                return {
                    "success": True,
                    "message": "No markdown files found",
                    "stats": {"processed": 0, "failed": 0},
                }

            stats = {"processed": 0, "failed": 0, "total_chunks": 0}

            for file_path in md_files:
                try:
                    # Get file content from git manager (works with both real and mock)
                    content = self.git_manager.get_file_content(file_path)
                    if not content:
                        stats["failed"] += 1
                        continue

                    # Process the file
                    document = self.processor.process_file(file_path, content)
                    if not document:
                        stats["failed"] += 1
                        continue

                    # Split into chunks for embedding
                    chunks = self.processor.split_content_for_embedding(document)

                    # Add to vector store
                    if self.vector_store.add_document(document, chunks):
                        stats["processed"] += 1
                        stats["total_chunks"] += len(chunks)
                    else:
                        stats["failed"] += 1

                except Exception as e:
                    print(f"Failed to process {file_path}: {e}")
                    stats["failed"] += 1

            return {
                "success": True,
                "message": f"Processed {stats['processed']} files, {stats['failed']} failed",
                "stats": stats,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def rebuild_index_stream(self) -> AsyncGenerator[Dict[str, any], None]:
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
            clear_result = self.vector_store.clear_collection()
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
            md_files = self.git_manager.get_all_markdown_files()

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
                    content = self.git_manager.get_file_content(file_path)
                    if not content:
                        stats["failed"] += 1
                        yield {
                            "type": "warning",
                            "message": f"No content found for: {file_path}",
                        }
                        continue

                    document = self.processor.process_file(file_path, content)
                    if not document:
                        stats["failed"] += 1
                        yield {
                            "type": "warning",
                            "message": f"Failed to process: {file_path}",
                        }
                        continue

                    chunks = self.processor.split_content_for_embedding(document)
                    if self.vector_store.add_document(document, chunks):
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

        except Exception as e:
            yield {"type": "error", "message": f"Build index failed: {str(e)}"}

    def incremental_sync(self) -> Dict[str, any]:
        """Perform incremental synchronization based on git changes."""
        print("Starting incremental sync...")

        try:
            # Get changed files
            changes = self.git_manager.get_changed_files()

            if not changes:
                return {
                    "success": True,
                    "message": "No changes detected",
                    "stats": {"processed": 0, "deleted": 0, "renamed": 0},
                }

            # Process file changes in vector store
            change_stats = self.vector_store.process_file_changes(changes)

            # Pull the latest changes
            if not self.git_manager.pull_changes():
                return {"success": False, "error": "Failed to pull changes"}

            # Process added/modified files
            stats = {
                "processed": 0,
                "failed": 0,
                "total_chunks": 0,
                "deleted": change_stats.get("deleted", 0),
                "renamed": change_stats.get("renamed", 0),
            }

            for change in changes:
                if change.status in [
                    FileStatus.ADDED,
                    FileStatus.MODIFIED,
                ]:  # Added or Modified
                    try:
                        # Get file content
                        content = self.git_manager.get_file_content(change.file_path)
                        if not content:
                            stats["failed"] += 1
                            continue

                        # Process the file
                        document = self.processor.process_file(
                            change.file_path, content
                        )
                        if not document:
                            stats["failed"] += 1
                            continue

                        # Split into chunks for embedding
                        chunks = self.processor.split_content_for_embedding(document)

                        # Add to vector store
                        if self.vector_store.add_document(document, chunks):
                            stats["processed"] += 1
                            stats["total_chunks"] += len(chunks)
                        else:
                            stats["failed"] += 1

                    except Exception as e:
                        print(f"Failed to process {change.file_path}: {e}")
                        stats["failed"] += 1

            return {
                "success": True,
                "message": f"Processed {len(changes)} changes",
                "stats": stats,
                "changes": [
                    {
                        "file_path": change.file_path,
                        "status": change.status.value,
                        "old_file_path": change.old_file_path,
                    }
                    for change in changes
                ],
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

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

    def get_repository_status(self) -> Dict[str, any]:
        """Get current repository and vector store status."""
        try:
            # Git status
            sync_info = self.git_manager.get_last_sync_info()

            # Vector store stats
            vector_stats = self.vector_store.get_stats()

            # Repository info
            repo_files = len(self.git_manager.get_all_markdown_files())

            repository_info = {
                "url": self.git_manager.repo_url,
                "local_path": str(self.git_manager.local_path),
                "branch": self.git_manager.branch,
                "total_md_files": repo_files,
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

    def cleanup_orphaned_embeddings(self) -> Dict[str, int]:
        """Remove embeddings for files that no longer exist in the repository."""
        try:
            # Get all files in vector store
            stored_files = set(self.vector_store.list_all_documents())

            # Get all files in repository
            repo_files = set(self.git_manager.get_all_markdown_files())

            # Find orphaned files
            orphaned_files = stored_files - repo_files

            if not orphaned_files:
                return {"removed": 0, "message": "No orphaned embeddings found"}

            # Remove orphaned embeddings
            removed_count = 0
            for file_path in orphaned_files:
                if self.vector_store.remove_document(file_path):
                    removed_count += 1

            return {
                "removed": removed_count,
                "total_orphaned": len(orphaned_files),
                "message": f"Removed {removed_count} orphaned embeddings",
            }

        except Exception as e:
            return {"error": str(e)}

    def force_reindex_file(self, file_path: str) -> Dict[str, any]:
        """Force re-indexing of a specific file."""
        try:
            content = self.git_manager.get_file_content(file_path)
            if not content:
                return {"success": False, "error": f"File not found: {file_path}"}

            # Process the file
            document = self.processor.process_file(file_path, content)
            if not document:
                return {
                    "success": False,
                    "error": f"Failed to process file: {file_path}",
                }

            # Split into chunks
            chunks = self.processor.split_content_for_embedding(document)

            # Add to vector store (this will remove existing chunks first)
            if self.vector_store.add_document(document, chunks):
                return {
                    "success": True,
                    "message": f"Re-indexed {file_path}",
                    "chunks": len(chunks),
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to add to vector store: {file_path}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def rebuild_index(self) -> Dict[str, any]:
        """Rebuild the entire vector index by clearing existing data and re-indexing all files."""
        try:
            print("🗑️  Clearing existing vector index...")

            # Clear the collection
            clear_result = self.vector_store.clear_collection()

            if not clear_result["success"]:
                return {"success": False, "error": clear_result["message"]}

            print("✅ Vector index cleared successfully")
            print("🔄 Starting full re-indexing...")

            # Perform full sync to rebuild index
            sync_result = self.full_sync()

            if sync_result["success"]:
                return {
                    "success": True,
                    "message": "Vector index rebuilt successfully",
                    "stats": sync_result["stats"],
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to rebuild index: {sync_result.get('error', 'Unknown error')}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}
