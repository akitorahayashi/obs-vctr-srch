"""Unit tests for VectorStore class."""

from pathlib import Path
from unittest.mock import Mock, patch

from src.config.settings import Settings
from src.models import VectorStore
from src.models.obsidian_processor import ObsidianDocument
from src.schemas import FileChange, FileStatus


class TestVectorStore:
    """Test cases for VectorStore class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Mock(spec=Settings)
        self.settings.VECTOR_DB_PATH = "./test_chroma_db"
        self.settings.EMBEDDING_MODEL_NAME = "test-model"

        with (
            patch(
                "src.models.vector_store.chromadb.PersistentClient"
            ) as self.mock_client_class,
            patch(
                "src.models.vector_store.SentenceTransformer"
            ) as self.mock_transformer_class,
            patch("builtins.print"),
        ):

            self.mock_client = self.mock_client_class.return_value
            self.mock_collection = Mock()
            self.mock_client.get_or_create_collection.return_value = (
                self.mock_collection
            )

            self.vector_store = VectorStore(settings=self.settings)

    def test_init(self):
        """Test VectorStore initialization."""
        assert self.vector_store.persist_directory == Path(self.settings.VECTOR_DB_PATH)
        assert self.vector_store.model_name == self.settings.EMBEDDING_MODEL_NAME
        self.mock_client_class.assert_called_once()
        self.mock_transformer_class.assert_called_once_with(
            self.settings.EMBEDDING_MODEL_NAME
        )
        self.mock_client.get_or_create_collection.assert_called_once()

    @patch("builtins.print")
    def test_add_document_success(self, mock_print):
        """Test successful document addition."""
        document = ObsidianDocument(
            file_path="test.md",
            title="Test",
            content="content",
            metadata={},
            tags=[],
            links=[],
        )
        chunks = [
            {"content": "Chunk 1", "metadata": {}},
            {"content": "Chunk 2", "metadata": {}},
        ]

        mock_embeddings = Mock()
        mock_embeddings.tolist.return_value = [[0.1], [0.2]]
        self.vector_store.embedding_model.encode.return_value = mock_embeddings

        with patch.object(self.vector_store, "remove_document", return_value=True):
            result = self.vector_store.add_document(document, chunks)

        assert result is True
        self.vector_store.collection.add.assert_called_once()
        call_args = self.vector_store.collection.add.call_args[1]
        assert len(call_args["ids"]) == 2

    def test_remove_document_success(self):
        """Test successful document removal."""
        file_path = "test.md"
        self.vector_store.collection.get.return_value = {"ids": ["id1", "id2"]}

        result = self.vector_store.remove_document(file_path)

        assert result is True
        self.vector_store.collection.delete.assert_called_once_with(ids=["id1", "id2"])

    def test_search_success(self):
        """Test successful document search."""
        query = "test query"
        mock_embeddings = Mock()
        mock_embeddings.tolist.return_value = [[0.1]]
        self.vector_store.embedding_model.encode.return_value = mock_embeddings

        mock_results = {
            "ids": [["doc1#0"]],
            "documents": [["content"]],
            "distances": [[0.1]],
            "metadatas": [
                [
                    {
                        "file_path": "doc1.md",
                        "title": "Doc1",
                        "chunk_index": 0,
                        "tags": "[]",
                        "links": "[]",
                        "created_at": None,
                        "modified_at": None,
                    }
                ]
            ],
        }
        self.vector_store.collection.query.return_value = mock_results

        results = self.vector_store.search(query)
        assert len(results) == 1
        assert results[0].id == "doc1#0"

    def test_process_file_changes(self):
        """Test processing file changes."""
        changes = [
            FileChange(file_path="deleted.md", status=FileStatus.DELETED),
            FileChange(
                file_path="renamed.md",
                status=FileStatus.RENAMED,
                old_file_path="old.md",
            ),
        ]

        with patch.object(self.vector_store, "remove_document") as mock_remove:
            mock_remove.return_value = True
            result = self.vector_store.process_file_changes(changes)

        # This method in VectorStore doesn't handle ADDED or MODIFIED, only DELETED and RENAMED
        # The logic in SyncCoordinator handles the ADD/MODIFIED cases.
        # So we expect added and updated to be 0.
        assert result["deleted"] == 1
        assert result["renamed"] == 1
        assert result["added"] == 0
        assert result["updated"] == 0
        mock_remove.assert_any_call("deleted.md")
        mock_remove.assert_any_call("old.md")
