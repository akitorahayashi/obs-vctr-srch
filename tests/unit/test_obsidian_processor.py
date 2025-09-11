"""Unit tests for ObsidianProcessor class."""

from datetime import datetime
from unittest.mock import Mock, patch

from src.services.obsidian_processor import ObsidianDocument, ObsidianProcessor


class TestObsidianProcessor:
    """Test cases for ObsidianProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ObsidianProcessor()

    @patch("tiktoken.get_encoding")
    def test_init_with_tokenizer(self, mock_get_encoding):
        """Test processor initialization with tokenizer."""
        mock_tokenizer = Mock()
        mock_get_encoding.return_value = mock_tokenizer

        processor = ObsidianProcessor()

        assert processor.tokenizer == mock_tokenizer
        mock_get_encoding.assert_called_once_with("cl100k_base")

    @patch("tiktoken.get_encoding")
    def test_init_without_tokenizer(self, mock_get_encoding):
        """Test processor initialization when tokenizer fails."""
        mock_get_encoding.side_effect = Exception("Tokenizer error")

        processor = ObsidianProcessor()

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

    def test_process_file_filename_title(self):
        """Test title extraction from filename when no H1 or title in metadata."""
        file_path = "my-document.md"
        content = "This document has no title or H1 heading."

        result = self.processor.process_file(file_path, content)

        assert result is not None
        assert result.title == "my-document"

    @patch("builtins.print")
    def test_process_file_error(self, mock_print):
        """Test processing file with error."""
        file_path = "error.md"
        # Invalid frontmatter that should cause an error
        content = "---\ninvalid yaml: [unclosed\n---\n# Content"

        with patch("frontmatter.loads", side_effect=Exception("Parse error")):
            result = self.processor.process_file(file_path, content)

        assert result is None
        mock_print.assert_called_with("Failed to process file error.md: Parse error")

    def test_extract_title_from_metadata(self):
        """Test title extraction from metadata."""
        file_path = "test.md"
        content = "Some content"
        metadata = {"title": "Metadata Title"}

        title = self.processor._extract_title(file_path, content, metadata)

        assert title == "Metadata Title"

    def test_extract_title_from_h1(self):
        """Test title extraction from H1 heading."""
        file_path = "test.md"
        content = """
Some intro text.

# Main Heading

More content here.
"""
        metadata = {}

        title = self.processor._extract_title(file_path, content, metadata)

        assert title == "Main Heading"

    def test_extract_title_from_filename(self):
        """Test title extraction from filename as fallback."""
        file_path = "my-test-file.md"
        content = "No title or H1 here."
        metadata = {}

        title = self.processor._extract_title(file_path, content, metadata)

        assert title == "my-test-file"

    def test_clean_content(self):
        """Test content cleaning functionality."""
        content = """
# Main Title

This is %%a comment%% regular text.

[[Internal Link]] and [[Another Link|Alias]]

[External Link](https://example.com)

![[image.png]]

![Alt text](image.jpg)

> [!note] This is a callout
> With some content

Multiple


Empty


Lines
"""

        cleaned = self.processor._clean_content(content)

        assert "%%a comment%%" not in cleaned
        assert "Internal Link" in cleaned
        assert "Another Link" in cleaned
        assert "[[" not in cleaned
        assert "External Link" in cleaned
        assert "(https://example.com)" not in cleaned
        assert "![[image.png]]" not in cleaned
        assert "![Alt text](image.jpg)" not in cleaned
        assert "[!note]" not in cleaned
        # Should have normalized whitespace
        assert "\n\n\n" not in cleaned

    def test_extract_tags_from_metadata(self):
        """Test tag extraction from metadata."""
        content = "Some content"
        metadata = {"tags": ["meta1", "meta2"]}

        tags = self.processor._extract_tags(content, metadata)

        assert "meta1" in tags
        assert "meta2" in tags

    def test_extract_tags_from_content(self):
        """Test tag extraction from content hashtags."""
        content = """
# Title

This has #tag1 and #tag2/subtag in it.

#another-tag at the beginning of line.
"""
        metadata = {}

        tags = self.processor._extract_tags(content, metadata)

        expected_tags = ["another-tag", "tag1", "tag2/subtag"]
        assert sorted(tags) == sorted(expected_tags)

    def test_extract_tags_mixed_sources(self):
        """Test tag extraction from both metadata and content."""
        content = "Content with #content-tag"
        metadata = {"tags": ["meta-tag"]}

        tags = self.processor._extract_tags(content, metadata)

        assert "meta-tag" in tags
        assert "content-tag" in tags

    def test_extract_tags_string_metadata(self):
        """Test tag extraction when metadata tags is a string."""
        content = "Some content"
        metadata = {"tags": "single-tag"}

        tags = self.processor._extract_tags(content, metadata)

        assert "single-tag" in tags

    def test_extract_links(self):
        """Test internal link extraction."""
        content = """
# Document

This has [[Simple Link]] and [[Link with Alias|Display Text]].

Also [[Another Link]] and [[Duplicate Link]] and [[Simple Link]] again.
"""

        links = self.processor._extract_links(content)

        expected_links = [
            "Another Link",
            "Duplicate Link",
            "Link with Alias",
            "Simple Link",
        ]
        assert sorted(links) == sorted(expected_links)

    def test_extract_datetime_formats(self):
        """Test datetime extraction from various formats."""
        # ISO format
        iso_date = "2023-01-01T10:30:00Z"
        result = self.processor._extract_datetime(iso_date)
        assert result is not None

        # Standard formats
        formats_to_test = [
            "2023-01-01 10:30:00",
            "2023-01-01 10:30",
            "2023-01-01",
            "01/01/2023",
            "01/01/2023",
        ]

        for date_str in formats_to_test:
            result = self.processor._extract_datetime(date_str)
            assert result is not None, f"Failed to parse: {date_str}"

        # Invalid format
        result = self.processor._extract_datetime("invalid-date")
        assert result is None

        # None input
        result = self.processor._extract_datetime(None)
        assert result is None

        # Already datetime object
        dt = datetime.now()
        result = self.processor._extract_datetime(dt)
        assert result == dt

    def test_count_tokens_with_tokenizer(self):
        """Test token counting with tokenizer."""
        mock_tokenizer = Mock()
        mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]
        self.processor.tokenizer = mock_tokenizer

        text = "This is test text"
        count = self.processor._count_tokens(text)

        assert count == 5
        mock_tokenizer.encode.assert_called_once_with(text)

    def test_count_tokens_without_tokenizer(self):
        """Test token counting without tokenizer (fallback)."""
        self.processor.tokenizer = None

        text = "This is a test text with twenty characters"  # 43 chars
        count = self.processor._count_tokens(text)

        expected = len(text) // 4  # Fallback estimation
        assert count == expected

    def test_count_tokens_error_fallback(self):
        """Test token counting with tokenizer error."""
        mock_tokenizer = Mock()
        mock_tokenizer.encode.side_effect = Exception("Encoding error")
        self.processor.tokenizer = mock_tokenizer

        text = "Test text"
        count = self.processor._count_tokens(text)

        expected = len(text) // 4  # Should fall back to estimation
        assert count == expected

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

    def test_split_content_for_embedding_multiple_paragraphs(self):
        """Test content splitting with multiple paragraphs."""
        content = "\n\n".join([f"Paragraph {i} content." for i in range(10)])

        document = ObsidianDocument(
            file_path="test.md",
            title="Test Document",
            content=content,
            metadata={"custom": "value"},
            tags=["test"],
            links=["link1"],
            word_count=30,
            token_count=30,
        )

        # Use small max_tokens to force splitting
        chunks = self.processor.split_content_for_embedding(document, max_tokens=10)

        assert len(chunks) > 1

        # Check first chunk structure
        first_chunk = chunks[0]
        assert first_chunk["file_path"] == "test.md"
        assert first_chunk["title"] == "Test Document"
        assert first_chunk["chunk_index"] == 0
        assert "test" in first_chunk["metadata"]["tags"]
        assert "link1" in first_chunk["metadata"]["links"]

    def test_split_content_long_paragraph(self):
        """Test content splitting with very long paragraph."""
        # Create a long paragraph that will need sentence-level splitting
        long_paragraph = ". ".join([f"Sentence {i}" for i in range(100)])

        document = ObsidianDocument(
            file_path="test.md",
            title="Test Document",
            content=long_paragraph,
            metadata={},
            tags=[],
            links=[],
            word_count=200,
            token_count=200,
        )

        chunks = self.processor.split_content_for_embedding(document, max_tokens=20)

        assert len(chunks) > 1

        # Each chunk should be within reasonable size
        for chunk in chunks:
            # Should contain some sentences
            assert len(chunk["content"]) > 0

    def test_create_chunk(self):
        """Test chunk creation with metadata."""
        document = ObsidianDocument(
            file_path="test.md",
            title="Test Document",
            content="Test content",
            metadata={"custom_field": "custom_value"},
            tags=["tag1", "tag2"],
            links=["link1"],
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            modified_at=datetime(2023, 1, 2, 10, 0, 0),
            word_count=10,
            token_count=15,
        )

        chunk = self.processor._create_chunk(document, "Chunk content", 0)

        assert chunk["file_path"] == "test.md"
        assert chunk["title"] == "Test Document"
        assert chunk["content"] == "Chunk content"
        assert chunk["chunk_index"] == 0
        assert chunk["metadata"]["tags"] == ["tag1", "tag2"]
        assert chunk["metadata"]["links"] == ["link1"]
        assert chunk["metadata"]["created_at"] == "2023-01-01T10:00:00"
        assert chunk["metadata"]["modified_at"] == "2023-01-02T10:00:00"


class TestObsidianDocument:
    """Test cases for ObsidianDocument model."""

    def test_obsidian_document_creation(self):
        """Test ObsidianDocument model creation."""
        document = ObsidianDocument(
            file_path="test.md",
            title="Test Document",
            content="Test content",
            metadata={"key": "value"},
            tags=["tag1", "tag2"],
            links=["link1", "link2"],
            created_at=datetime(2023, 1, 1),
            modified_at=datetime(2023, 1, 2),
            word_count=10,
            token_count=15,
        )

        assert document.file_path == "test.md"
        assert document.title == "Test Document"
        assert document.content == "Test content"
        assert document.metadata == {"key": "value"}
        assert document.tags == ["tag1", "tag2"]
        assert document.links == ["link1", "link2"]
        assert document.created_at == datetime(2023, 1, 1)
        assert document.modified_at == datetime(2023, 1, 2)
        assert document.word_count == 10
        assert document.token_count == 15

    def test_obsidian_document_defaults(self):
        """Test ObsidianDocument model with default values."""
        document = ObsidianDocument(
            file_path="test.md",
            title="Test Document",
            content="Test content",
            metadata={},
            tags=[],
            links=[],
        )

        assert document.created_at is None
        assert document.modified_at is None
        assert document.word_count == 0
        assert document.token_count == 0
