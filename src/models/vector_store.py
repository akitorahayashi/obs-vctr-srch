import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from sentence_transformers import SentenceTransformer

from src.config.settings import Settings
from src.schemas import FileChange, FileStatus, SearchResult

from .obsidian_processor import ObsidianDocument


class VectorStore:
    """Manages vector embeddings with incremental update capabilities."""

    def __init__(self, settings: Settings):
        self.collection_name = "obsidian_vault"  # Hardcoded, not from settings
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.persist_directory = Path(settings.VECTOR_DB_PATH)

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(self.model_name)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description": "Obsidian vault embeddings",
                "model_name": self.model_name,
            },
        )

        print(f"Vector store initialized with {self.collection.count()} documents")

    def add_document(self, document: ObsidianDocument, chunks: List[Dict]) -> bool:
        """Add a document and its chunks to the vector store."""
        try:
            # First, remove any existing chunks for this file
            self.remove_document(document.file_path)

            if not chunks:
                print(f"No chunks to add for {document.file_path}")
                return True

            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document.file_path}#chunk_{i}"
                ids.append(chunk_id)
                documents.append(chunk["content"])

                # Prepare metadata (ensure no None values)
                metadata = {
                    "file_path": document.file_path or "",
                    "title": document.title or "",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "word_count": document.word_count or 0,
                    "token_count": document.token_count or 0,
                    "tags": json.dumps(document.tags or []),
                    "links": json.dumps(document.links or []),
                    "created_at": (
                        document.created_at.isoformat() if document.created_at else ""
                    ),
                    "modified_at": (
                        document.modified_at.isoformat() if document.modified_at else ""
                    ),
                    "indexed_at": datetime.now().isoformat(),
                }

                # Add custom metadata
                for key, value in chunk.get("metadata", {}).items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[f"custom_{key}"] = value
                    elif value is not None:
                        metadata[f"custom_{key}"] = str(value)

                metadatas.append(metadata)

            # Generate embeddings
            embeddings = self.embedding_model.encode(documents, show_progress_bar=False)

            # Add to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings.tolist(),
            )

            print(f"Added {len(chunks)} chunks for {document.file_path}")
            return True

        except Exception as e:
            print(f"Failed to add document {document.file_path}: {e}")
            return False

    def remove_document(self, file_path: str) -> bool:
        """Remove all chunks for a specific file."""
        try:
            # Query for all chunks of this file
            results = self.collection.get(where={"file_path": file_path})

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                print(f"Removed {len(results['ids'])} chunks for {file_path}")

            return True

        except Exception as e:
            print(f"Failed to remove document {file_path}: {e}")
            return False

    def search(
        self,
        query: str,
        n_results: int = 10,
        file_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        try:
            # Build where clause for filtering
            where_clause = {}

            if file_filter:
                where_clause["file_path"] = {"$regex": file_filter}

            # Note: ChromaDB doesn't support complex JSON array queries easily
            # For tag filtering, we'd need to implement it post-query

            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                [query], show_progress_bar=False
            )

            # Search
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"],
            )

            # Format results
            formatted_results = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]

                # Parse JSON fields
                tags = json.loads(metadata.get("tags", "[]"))
                links = json.loads(metadata.get("links", "[]"))

                # Apply tag filtering if specified
                if tag_filter:
                    if not any(tag in tags for tag in tag_filter):
                        continue

                result = SearchResult(
                    id=results["ids"][0][i],
                    content=results["documents"][0][i],
                    distance=results["distances"][0][i],
                    file_path=metadata["file_path"],
                    title=metadata["title"],
                    chunk_index=metadata["chunk_index"],
                    tags=tags,
                    links=links,
                    created_at=metadata.get("created_at"),
                    modified_at=metadata.get("modified_at"),
                )

                formatted_results.append(result)

            return formatted_results

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    def get_document_info(self, file_path: str) -> Optional[Dict]:
        """Get information about a document in the store."""
        try:
            results = self.collection.get(
                where={"file_path": file_path}, limit=1, include=["metadatas"]
            )

            if results["ids"]:
                metadata = results["metadatas"][0]
                return {
                    "file_path": metadata["file_path"],
                    "title": metadata["title"],
                    "total_chunks": metadata["total_chunks"],
                    "indexed_at": metadata["indexed_at"],
                    "tags": json.loads(metadata.get("tags", "[]")),
                }

            return None

        except Exception as e:
            print(f"Failed to get document info for {file_path}: {e}")
            return None

    def list_all_documents(self) -> List[str]:
        """Get list of all document file paths in the store."""
        try:
            # Get all unique file paths
            results = self.collection.get(include=["metadatas"])
            file_paths = set()

            for metadata in results["metadatas"]:
                file_paths.add(metadata["file_path"])

            return sorted(list(file_paths))

        except Exception as e:
            print(f"Failed to list documents: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get statistics about the vector store."""
        try:
            total_chunks = self.collection.count()
            all_docs = self.list_all_documents()

            # Get tag distribution
            results = self.collection.get(include=["metadatas"])
            tag_counts = {}

            for metadata in results["metadatas"]:
                tags = json.loads(metadata.get("tags", "[]"))
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

            return {
                "total_documents": len(all_docs),
                "total_chunks": total_chunks,
                "top_tags": sorted(
                    tag_counts.items(), key=lambda x: x[1], reverse=True
                )[:20],
                "model_name": self.model_name,
                "collection_name": self.collection_name,
            }

        except Exception as e:
            print(f"Failed to get stats: {e}")
            return {}

    def process_file_changes(self, changes: List[FileChange]) -> Dict[str, int]:
        """Process a list of file changes and update the vector store accordingly."""
        stats = {"added": 0, "updated": 0, "deleted": 0, "renamed": 0}

        for change in changes:
            if change.status == FileStatus.DELETED:
                if self.remove_document(change.file_path):
                    stats["deleted"] += 1

            elif change.status == FileStatus.RENAMED:
                if change.old_file_path and self.remove_document(change.old_file_path):
                    stats["renamed"] += 1
                # New file will be handled by the sync process

        return stats

    def check_model_compatibility(self) -> Dict[str, any]:
        """Check if the current model matches the stored model in collection metadata."""
        try:
            collection_metadata = self.collection.metadata
            stored_model = collection_metadata.get("model_name", "unknown")

            if stored_model != self.model_name:
                return {
                    "compatible": False,
                    "stored_model": stored_model,
                    "current_model": self.model_name,
                    "message": f"Model changed from {stored_model} to {self.model_name}",
                }

            return {
                "compatible": True,
                "stored_model": stored_model,
                "current_model": self.model_name,
                "message": "Model is compatible",
            }

        except Exception as e:
            # If we can't get metadata, assume incompatible to be safe
            return {
                "compatible": False,
                "stored_model": "unknown",
                "current_model": self.model_name,
                "message": f"Could not verify model compatibility: {e}",
            }

    def clear_collection(self) -> Dict[str, any]:
        """Clear all documents from the collection and update metadata."""
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)

            # Recreate the collection with updated metadata
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Obsidian vault embeddings",
                    "model_name": self.model_name,
                },
            )

            return {
                "success": True,
                "message": f"Collection cleared and recreated with model {self.model_name}",
            }

        except Exception as e:
            return {"success": False, "message": f"Failed to clear collection: {e}"}
