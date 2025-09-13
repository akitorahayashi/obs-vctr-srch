"""Coordinates synchronization between Git repository and vector store."""

from pathlib import Path
from typing import Dict, List, Optional

from .git_manager import GitManager
from .obsidian_processor import ObsidianProcessor
from .vector_store import VectorStore


class SyncCoordinator:
    """Coordinates synchronization between git repo and vector embeddings."""

    def __init__(
        self,
        repo_url: str,
        local_path: str,
        vector_store_path: str = "./chroma_db",
        branch: str = "main",
        github_token: str = "",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.git_manager = GitManager(repo_url, local_path, branch, github_token)
        self.processor = ObsidianProcessor()
        self.vector_store = VectorStore(
            persist_directory=vector_store_path, model_name=embedding_model
        )

        self.local_path = Path(local_path)

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
            # Get all markdown files
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
                    # Get file content
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
                if change.change_type in ["A", "M"]:  # Added or Modified
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
                        "change_type": change.change_type,
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

            return {
                "repository": {
                    "url": self.git_manager.repo_url,
                    "local_path": str(self.git_manager.local_path),
                    "branch": self.git_manager.branch,
                    "last_commit": sync_info,
                    "total_md_files": repo_files,
                },
                "vector_store": vector_stats,
                "sync_status": "ready",
            }

        except Exception as e:
            return {"error": str(e)}

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
