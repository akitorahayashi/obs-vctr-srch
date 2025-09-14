"""Unit tests for VectorStore class."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.models import FileChange
from src.services.obsidian_processor import ObsidianDocument
from src.services.vector_store import VectorStore


class TestVectorStore:
    """Test cases for VectorStore class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.persist_directory = "./test_chroma_db"
        self.collection_name = "test_collection"
        self.model_name = "test-model"

        with (
            patch("src.services.vector_store.chromadb.PersistentClient"),
            patch("src.services.vector_store.SentenceTransformer"),
            patch("builtins.print"),
        ):

            self.vector_store = VectorStore(
                persist_directory=self.persist_directory,
                collection_name=self.collection_name,
                model_name=self.model_name,
            )

            # Mock the collection
            self.vector_store.collection = Mock()
            self.vector_store.collection.count.return_value = 0

    def test_init(self):
        """Test VectorStore initialization."""
        assert self.vector_store.persist_directory == Path(self.persist_directory)
        assert self.vector_store.collection_name == self.collection_name
        assert self.vector_store.model_name == self.model_name

    @patch("builtins.print")
    def test_add_document_success(self, mock_print):
        """Test successful document addition."""
        # Create test document
        document = ObsidianDocument(
            file_path="test.md",
            title="Test Document",
            content="Test content",
            metadata={"custom": "value"},
            tags=["tag1", "tag2"],
            links=["link1"],
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            modified_at=datetime(2023, 1, 2, 10, 0, 0),
            word_count=10,
            token_count=15,
        )

        chunks = [
            {"content": "Chunk 1 content", "metadata": {}},
            {"content": "Chunk 2 content", "metadata": {"extra": "data"}},
        ]

        # Mock embedding model
        mock_embeddings = Mock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        self.vector_store.embedding_model.encode.return_value = mock_embeddings

        # Mock remove_document (should be called first)
        with patch.object(self.vector_store, "remove_document", return_value=True):
            result = self.vector_store.add_document(document, chunks)

        assert result is True

        # Verify collection.add was called
        self.vector_store.collection.add.assert_called_once()
        call_args = self.vector_store.collection.add.call_args[1]

        assert len(call_args["ids"]) == 2
        assert call_args["ids"][0] == "test.md#chunk_0"
        assert call_args["ids"][1] == "test.md#chunk_1"
        assert call_args["documents"] == ["Chunk 1 content", "Chunk 2 content"]
        assert call_args["embeddings"] == [[0.1, 0.2], [0.3, 0.4]]

        # Check metadata structure
        metadata1 = call_args["metadatas"][0]
        assert metadata1["file_path"] == "test.md"
        assert metadata1["title"] == "Test Document"
        assert metadata1["chunk_index"] == 0
        assert metadata1["total_chunks"] == 2
        assert json.loads(metadata1["tags"]) == ["tag1", "tag2"]
        assert json.loads(metadata1["links"]) == ["link1"]

    @patch("builtins.print")
    def test_add_document_no_chunks(self, mock_print):
        """Test adding document with no chunks."""
        document = ObsidianDocument(
            file_path="test.md",
            title="Test",
            content="content",
            metadata={},
            tags=[],
            links=[],
        )

        with patch.object(self.vector_store, "remove_document", return_value=True):
            result = self.vector_store.add_document(document, [])

        assert result is True
        mock_print.assert_called_with("No chunks to add for test.md")
        self.vector_store.collection.add.assert_not_called()

    @patch("builtins.print")
    def test_add_document_exception(self, mock_print):
        """Test document addition with exception."""
        document = ObsidianDocument(
            file_path="test.md",
            title="Test",
            content="content",
            metadata={},
            tags=[],
            links=[],
        )
        chunks = [{"content": "test", "metadata": {}}]

        self.vector_store.embedding_model.encode.side_effect = Exception(
            "Encoding error"
        )

        with patch.object(self.vector_store, "remove_document", return_value=True):
            result = self.vector_store.add_document(document, chunks)

        assert result is False
        mock_print.assert_called_with("Failed to add document test.md: Encoding error")

    @patch("builtins.print")
    def test_remove_document_success(self, mock_print):
        """Test successful document removal."""
        file_path = "test.md"

        # Mock collection.get to return existing chunks
        self.vector_store.collection.get.return_value = {
            "ids": ["test.md#chunk_0", "test.md#chunk_1"]
        }

        result = self.vector_store.remove_document(file_path)

        assert result is True
        self.vector_store.collection.get.assert_called_once_with(
            where={"file_path": file_path}
        )
        self.vector_store.collection.delete.assert_called_once_with(
            ids=["test.md#chunk_0", "test.md#chunk_1"]
        )
        mock_print.assert_called_with("Removed 2 chunks for test.md")

    @patch("builtins.print")
    def test_remove_document_no_chunks(self, mock_print):
        """Test removing document with no existing chunks."""
        file_path = "test.md"

        self.vector_store.collection.get.return_value = {"ids": []}

        result = self.vector_store.remove_document(file_path)

        assert result is True
        self.vector_store.collection.delete.assert_not_called()

    @patch("builtins.print")
    def test_remove_document_exception(self, mock_print):
        """Test document removal with exception."""
        file_path = "test.md"

        self.vector_store.collection.get.side_effect = Exception("Remove error")

        result = self.vector_store.remove_document(file_path)

        assert result is False
        mock_print.assert_called_with("Failed to remove document test.md: Remove error")

    def test_search_success(self):
        """Test successful document search."""
        query = "test query"

        # Mock embedding generation
        mock_embeddings = Mock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2, 0.3]]
        self.vector_store.embedding_model.encode.return_value = mock_embeddings

        # Mock collection search results
        mock_results = {
            "ids": [["doc1#chunk_0", "doc2#chunk_0"]],
            "documents": [["Document 1 content", "Document 2 content"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [
                [
                    {
                        "file_path": "doc1.md",
                        "title": "Document 1",
                        "chunk_index": 0,
                        "tags": '["tag1", "tag2"]',
                        "links": '["link1"]',
                        "created_at": "2023-01-01T10:00:00",
                        "modified_at": "2023-01-02T10:00:00",
                    },
                    {
                        "file_path": "doc2.md",
                        "title": "Document 2",
                        "chunk_index": 0,
                        "tags": '["tag3"]',
                        "links": "[]",
                        "created_at": "",
                        "modified_at": "",
                    },
                ]
            ],
        }
        self.vector_store.collection.query.return_value = mock_results

        result = self.vector_store.search(query, n_results=10)

        assert len(result) == 2

        # Check first result
        first_result = result[0]
        assert first_result.id == "doc1#chunk_0"
        assert first_result.content == "Document 1 content"
        assert first_result.distance == 0.1
        assert first_result.file_path == "doc1.md"
        assert first_result.title == "Document 1"
        assert first_result.tags == ["tag1", "tag2"]
        assert first_result.links == ["link1"]

    def test_search_with_filters(self):
        """Test search with file and tag filters."""
        query = "test query"
        file_filter = "*.md"
        tag_filter = ["tag1"]

        # Mock embedding and results
        mock_embeddings = Mock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2, 0.3]]
        self.vector_store.embedding_model.encode.return_value = mock_embeddings
        mock_results = {
            "ids": [["doc1#chunk_0"]],
            "documents": [["Document 1 content"]],
            "distances": [[0.1]],
            "metadatas": [
                [
                    {
                        "file_path": "doc1.md",
                        "title": "Document 1",
                        "chunk_index": 0,
                        "tags": '["tag1", "tag2"]',
                        "links": "[]",
                        "created_at": "",
                        "modified_at": "",
                    }
                ]
            ],
        }
        self.vector_store.collection.query.return_value = mock_results

        result = self.vector_store.search(
            query, n_results=5, file_filter=file_filter, tag_filter=tag_filter
        )

        assert len(result) == 1

        # Verify query was called with file filter
        self.vector_store.collection.query.assert_called_once()
        call_args = self.vector_store.collection.query.call_args[1]
        assert call_args["where"] == {"file_path": {"$regex": file_filter}}

    def test_search_tag_filter_exclusion(self):
        """Test search with tag filter that excludes results."""
        query = "test query"
        tag_filter = ["nonexistent_tag"]

        # Mock results without the required tag
        mock_embeddings = Mock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2, 0.3]]
        self.vector_store.embedding_model.encode.return_value = mock_embeddings
        mock_results = {
            "ids": [["doc1#chunk_0"]],
            "documents": [["Document 1 content"]],
            "distances": [[0.1]],
            "metadatas": [
                [
                    {
                        "file_path": "doc1.md",
                        "title": "Document 1",
                        "chunk_index": 0,
                        "tags": '["different_tag"]',
                        "links": "[]",
                        "created_at": "",
                        "modified_at": "",
                    }
                ]
            ],
        }
        self.vector_store.collection.query.return_value = mock_results

        result = self.vector_store.search(query, tag_filter=tag_filter)

        # Result should be filtered out due to tag mismatch
        assert len(result) == 0

    @patch("builtins.print")
    def test_search_exception(self, mock_print):
        """Test search with exception."""
        query = "test query"

        self.vector_store.embedding_model.encode.side_effect = Exception("Search error")

        result = self.vector_store.search(query)

        assert result == []
        mock_print.assert_called_with("Search failed: Search error")

    def test_get_document_info_success(self):
        """Test successful document info retrieval."""
        file_path = "test.md"

        mock_results = {
            "ids": ["test.md#chunk_0"],
            "metadatas": [
                {
                    "file_path": "test.md",
                    "title": "Test Document",
                    "total_chunks": 3,
                    "indexed_at": "2023-01-01T10:00:00",
                    "tags": '["tag1", "tag2"]',
                }
            ],
        }
        self.vector_store.collection.get.return_value = mock_results

        result = self.vector_store.get_document_info(file_path)

        expected = {
            "file_path": "test.md",
            "title": "Test Document",
            "total_chunks": 3,
            "indexed_at": "2023-01-01T10:00:00",
            "tags": ["tag1", "tag2"],
        }
        assert result == expected

    def test_get_document_info_not_found(self):
        """Test document info retrieval when document doesn't exist."""
        file_path = "nonexistent.md"

        self.vector_store.collection.get.return_value = {"ids": []}

        result = self.vector_store.get_document_info(file_path)

        assert result is None

    @patch("builtins.print")
    def test_get_document_info_exception(self, mock_print):
        """Test document info retrieval with exception."""
        file_path = "test.md"

        self.vector_store.collection.get.side_effect = Exception("Info error")

        result = self.vector_store.get_document_info(file_path)

        assert result is None
        mock_print.assert_called_with(
            "Failed to get document info for test.md: Info error"
        )

    def test_list_all_documents_success(self):
        """Test successful listing of all documents."""
        mock_results = {
            "metadatas": [
                {"file_path": "doc1.md"},
                {"file_path": "doc2.md"},
                {"file_path": "doc1.md"},  # Duplicate should be deduplicated
                {"file_path": "doc3.md"},
            ]
        }
        self.vector_store.collection.get.return_value = mock_results

        result = self.vector_store.list_all_documents()

        expected = ["doc1.md", "doc2.md", "doc3.md"]
        assert sorted(result) == sorted(expected)

    @patch("builtins.print")
    def test_list_all_documents_exception(self, mock_print):
        """Test listing documents with exception."""
        self.vector_store.collection.get.side_effect = Exception("List error")

        result = self.vector_store.list_all_documents()

        assert result == []
        mock_print.assert_called_with("Failed to list documents: List error")

    def test_get_stats_success(self):
        """Test successful stats retrieval."""
        # Mock collection count
        self.vector_store.collection.count.return_value = 10

        # Mock list_all_documents
        with patch.object(
            self.vector_store, "list_all_documents", return_value=["doc1.md", "doc2.md"]
        ):
            # Mock collection.get for tag statistics
            mock_results = {
                "metadatas": [
                    {"tags": '["tag1", "tag2"]'},
                    {"tags": '["tag1", "tag3"]'},
                    {"tags": '["tag2"]'},
                ]
            }
            self.vector_store.collection.get.return_value = mock_results

            result = self.vector_store.get_stats()

        assert result["total_documents"] == 2
        assert result["total_chunks"] == 10
        assert result["model_name"] == self.model_name

    def test_check_model_compatibility_compatible(self):
        """Test model compatibility check when models match."""
        # Mock collection metadata with same model
        self.vector_store.collection.metadata = {"model_name": self.model_name}

        result = self.vector_store.check_model_compatibility()

        assert result["compatible"] is True
        assert result["stored_model"] == self.model_name
        assert result["current_model"] == self.model_name
        assert "compatible" in result["message"]

    def test_check_model_compatibility_incompatible(self):
        """Test model compatibility check when models differ."""
        old_model = "old-model"
        # Mock collection metadata with different model
        self.vector_store.collection.metadata = {"model_name": old_model}

        result = self.vector_store.check_model_compatibility()

        assert result["compatible"] is False
        assert result["stored_model"] == old_model
        assert result["current_model"] == self.model_name
        assert "changed from" in result["message"]

    def test_check_model_compatibility_no_metadata(self):
        """Test model compatibility check with no stored model metadata."""
        # Mock collection metadata without model_name
        self.vector_store.collection.metadata = {"description": "test"}

        result = self.vector_store.check_model_compatibility()

        assert result["compatible"] is False
        assert result["stored_model"] == "unknown"
        assert result["current_model"] == self.model_name

    def test_check_model_compatibility_exception(self):
        """Test model compatibility check when metadata access fails."""
        # Mock exception when accessing metadata
        self.vector_store.collection.metadata = Mock()
        self.vector_store.collection.metadata.get = Mock(
            side_effect=Exception("Metadata error")
        )

        result = self.vector_store.check_model_compatibility()

        assert result["compatible"] is False
        assert result["stored_model"] == "unknown"
        assert result["current_model"] == self.model_name
        assert "Could not verify" in result["message"]

    @patch("src.services.vector_store.chromadb.PersistentClient")
    def test_clear_collection_success(self, mock_client_class):
        """Test successful collection clearing."""
        # Mock client and collection operations
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        self.vector_store.client = mock_client

        mock_new_collection = Mock()
        mock_client.create_collection.return_value = mock_new_collection

        result = self.vector_store.clear_collection()

        # Verify delete and create were called
        mock_client.delete_collection.assert_called_once_with(name=self.collection_name)
        mock_client.create_collection.assert_called_once_with(
            name=self.collection_name,
            metadata={
                "description": "Obsidian vault embeddings",
                "model_name": self.model_name,
            },
        )

        assert result["success"] is True
        assert self.model_name in result["message"]
        assert self.vector_store.collection == mock_new_collection

    def test_clear_collection_failure(self):
        """Test collection clearing failure."""
        # Mock client to raise exception
        self.vector_store.client.delete_collection.side_effect = Exception(
            "Delete failed"
        )

        result = self.vector_store.clear_collection()

        assert result["success"] is False
        assert "Failed to clear collection" in result["message"]

    @patch("builtins.print")
    def test_get_stats_exception(self, mock_print):
        """Test stats retrieval with exception."""
        self.vector_store.collection.count.side_effect = Exception("Stats error")

        result = self.vector_store.get_stats()

        assert result == {}
        mock_print.assert_called_with("Failed to get stats: Stats error")

    def test_process_file_changes(self):
        """Test processing file changes."""
        changes = [
            FileChange(file_path="deleted.md", change_type="D"),
            FileChange(
                file_path="renamed.md", change_type="R", old_file_path="old_name.md"
            ),
            FileChange(file_path="modified.md", change_type="M"),
        ]

        # Mock remove_document calls
        with patch.object(self.vector_store, "remove_document") as mock_remove:
            mock_remove.side_effect = [True, True]  # Success for both removes

            result = self.vector_store.process_file_changes(changes)

        assert result["deleted"] == 1
        assert result["renamed"] == 1
        assert result["added"] == 0
        assert result["updated"] == 0

        # Verify remove_document was called correctly
        assert mock_remove.call_count == 2
        mock_remove.assert_any_call("deleted.md")
        mock_remove.assert_any_call("old_name.md")

    def test_process_file_changes_no_old_path(self):
        """Test processing renamed file without old path."""
        changes = [
            FileChange(file_path="renamed.md", change_type="R", old_file_path=None)
        ]

        with patch.object(self.vector_store, "remove_document") as mock_remove:
            result = self.vector_store.process_file_changes(changes)

        assert result["renamed"] == 0
        mock_remove.assert_not_called()

    def test_process_file_changes_remove_failure(self):
        """Test processing file changes when remove fails."""
        changes = [FileChange(file_path="deleted.md", change_type="D")]

        with patch.object(self.vector_store, "remove_document", return_value=False):
            result = self.vector_store.process_file_changes(changes)

        assert result["deleted"] == 0
