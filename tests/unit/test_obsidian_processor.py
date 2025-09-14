"""Unit tests for ObsidianProcessor class."""

from datetime import datetime
from unittest.mock import Mock, patch

from src.config.settings import Settings
from src.models import ObsidianProcessor
from src.models.obsidian_processor import ObsidianDocument


class TestObsidianProcessor:
    """Test cases for ObsidianProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Mock(spec=Settings)
        self.processor = ObsidianProcessor(settings=self.settings)

    @patch("tiktoken.get_encoding")
    def test_init_with_tokenizer(self, mock_get_encoding):
        """Test processor initialization with tokenizer."""
        mock_tokenizer = Mock()
        mock_get_encoding.return_value = mock_tokenizer

        processor = ObsidianProcessor(settings=self.settings)

        assert processor.tokenizer == mock_tokenizer
        mock_get_encoding.assert_called_once_with("cl100k_base")

    @patch("tiktoken.get_encoding")
    def test_init_without_tokenizer(self, mock_get_encoding):
        """Test processor initialization when tokenizer fails."""
        mock_get_encoding.side_effect = Exception("Tokenizer error")

        processor = ObsidianProcessor(settings=self.settings)

        assert processor.tokenizer is None

    def test_process_file_simple(self):
        """Test processing a simple markdown file."""
        file_path = "test.md"
        content = """---
title: Test Document
tags: [test, markdown]
created: 2023-01-01T10:00:00
---

# Test Document

This is a simple test document with some content.

#additional-tag

[[Internal Link]] and [[Another Link|Alias]]
"""

        result = self.processor.process_file(file_path, content)

        assert result is not None
        assert result.file_path == file_path
        assert result.title == "Test Document"
        assert "This is a simple test document with some content." in result.content
        assert "test" in result.tags
        assert "markdown" in result.tags
        assert "additional-tag" in result.tags
        assert "Internal Link" in result.links
        assert "Another Link" in result.links
        assert result.created_at == datetime(2023, 1, 1, 10, 0, 0)

    def test_process_file_no_frontmatter(self):
        """Test processing a file without frontmatter."""
        file_path = "simple.md"
        content = """# Simple Document

This is content without frontmatter.

#tag1 #tag2

[[Link One]] and [[Link Two]]
"""

        result = self.processor.process_file(file_path, content)

        assert result is not None
        assert result.file_path == file_path
        assert result.title == "Simple Document"
        assert "tag1" in result.tags
        assert "tag2" in result.tags
        assert "Link One" in result.links
        assert "Link Two" in result.links

    def test_split_content_for_embedding_simple(self):
        """Test content splitting for embedding with simple content."""
        document = ObsidianDocument(
            file_path="test.md",
            title="Test Document",
            content="Short content that fits in one chunk.",
            metadata={},
            tags=["test"],
            links=[],
            word_count=8,
            token_count=8,
        )

        chunks = self.processor.split_content_for_embedding(document, max_tokens=500)

        assert len(chunks) == 1
        assert chunks[0]["file_path"] == "test.md"
        assert chunks[0]["title"] == "Test Document"
        assert chunks[0]["content"] == "Short content that fits in one chunk."
        assert chunks[0]["chunk_index"] == 0
