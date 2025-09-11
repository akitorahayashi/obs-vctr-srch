import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import frontmatter
import tiktoken
from pydantic import BaseModel


class ObsidianDocument(BaseModel):
    """Represents a processed Obsidian document."""

    file_path: str
    title: str
    content: str
    metadata: Dict
    tags: List[str]
    links: List[str]
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    word_count: int = 0
    token_count: int = 0


class ObsidianProcessor:
    """Processes Obsidian vault files and extracts structured information."""

    def __init__(self):
        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def process_file(self, file_path: str, content: str) -> Optional[ObsidianDocument]:
        """Process a single Obsidian markdown file."""
        try:
            # Parse frontmatter
            post = frontmatter.loads(content)
            metadata = post.metadata
            body_content = post.content

            # Extract title
            title = self._extract_title(file_path, body_content, metadata)

            # Clean and process content
            cleaned_content = self._clean_content(body_content)

            # Extract tags
            tags = self._extract_tags(body_content, metadata)

            # Extract internal links
            links = self._extract_links(body_content)

            # Count words and tokens
            word_count = len(cleaned_content.split())
            token_count = self._count_tokens(cleaned_content)

            # Extract timestamps from metadata or file system
            created_at = self._extract_datetime(metadata.get("created"))
            modified_at = self._extract_datetime(metadata.get("modified"))

            return ObsidianDocument(
                file_path=file_path,
                title=title,
                content=cleaned_content,
                metadata=metadata,
                tags=tags,
                links=links,
                created_at=created_at,
                modified_at=modified_at,
                word_count=word_count,
                token_count=token_count,
            )

        except Exception as e:
            print(f"Failed to process file {file_path}: {e}")
            return None

    def _extract_title(self, file_path: str, content: str, metadata: Dict) -> str:
        """Extract title from metadata, content, or filename."""
        # Try metadata first
        if "title" in metadata:
            return metadata["title"]

        # Try first H1 heading
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

        # Fall back to filename
        return Path(file_path).stem

    def _clean_content(self, content: str) -> str:
        """Clean Obsidian-specific syntax from content."""
        # Remove comments
        content = re.sub(r"%%.*?%%", "", content, flags=re.DOTALL)

        # Convert internal links to plain text
        content = re.sub(r"\[\[([^\]]+)\]\]", r"\1", content)

        # Convert external links to plain text
        content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)

        # Remove image syntax
        content = re.sub(r"!\[\[([^\]]+)\]\]", "", content)
        content = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", content)

        # Remove callouts
        content = re.sub(r">\s*\[!(.*?)\].*$", "", content, flags=re.MULTILINE)

        # Remove excessive whitespace
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = content.strip()

        return content

    def _extract_tags(self, content: str, metadata: Dict) -> List[str]:
        """Extract tags from content and metadata."""
        tags = set()

        # From metadata
        if "tags" in metadata:
            if isinstance(metadata["tags"], list):
                tags.update(metadata["tags"])
            elif isinstance(metadata["tags"], str):
                tags.add(metadata["tags"])

        # From content (hashtags)
        hashtag_pattern = r"(?:^|\s)#([a-zA-Z0-9_/-]+)"
        hashtags = re.findall(hashtag_pattern, content, re.MULTILINE)
        tags.update(hashtags)

        return sorted(list(tags))

    def _extract_links(self, content: str) -> List[str]:
        """Extract internal links from content."""
        # Find all [[link]] patterns
        links = re.findall(r"\[\[([^\]]+)\]\]", content)

        # Clean up links (remove aliases)
        cleaned_links = []
        for link in links:
            # Handle aliases (link|alias)
            if "|" in link:
                link = link.split("|")[0]
            cleaned_links.append(link.strip())

        return sorted(list(set(cleaned_links)))

    def _extract_datetime(self, value) -> Optional[datetime]:
        """Extract datetime from various formats."""
        if not value:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                # Try common formats
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                ]:
                    try:
                        return datetime.strptime(value, fmt)
                    except Exception:
                        pass

        return None

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass

        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4

    def split_content_for_embedding(
        self, document: ObsidianDocument, max_tokens: int = 500
    ) -> List[Dict]:
        """Split document content into chunks for embedding."""
        chunks = []
        content = document.content

        # Split by paragraphs first
        paragraphs = content.split("\n\n")

        current_chunk = ""
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = self._count_tokens(paragraph)

            # If this paragraph alone exceeds max_tokens, split it further
            if paragraph_tokens > max_tokens:
                if current_chunk:
                    chunks.append(
                        self._create_chunk(document, current_chunk, len(chunks))
                    )
                    current_chunk = ""
                    current_tokens = 0

                # Split long paragraph into sentences
                sentences = re.split(r"[.!?]+", paragraph)
                temp_chunk = ""
                temp_tokens = 0

                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    sentence_tokens = self._count_tokens(sentence)

                    if temp_tokens + sentence_tokens > max_tokens and temp_chunk:
                        chunks.append(
                            self._create_chunk(document, temp_chunk, len(chunks))
                        )
                        temp_chunk = sentence
                        temp_tokens = sentence_tokens
                    else:
                        temp_chunk += sentence + ". "
                        temp_tokens += sentence_tokens

                if temp_chunk:
                    current_chunk = temp_chunk
                    current_tokens = temp_tokens

            elif current_tokens + paragraph_tokens > max_tokens and current_chunk:
                chunks.append(self._create_chunk(document, current_chunk, len(chunks)))
                current_chunk = paragraph
                current_tokens = paragraph_tokens
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
                current_tokens += paragraph_tokens

        if current_chunk:
            chunks.append(self._create_chunk(document, current_chunk, len(chunks)))

        return chunks

    def _create_chunk(
        self, document: ObsidianDocument, content: str, chunk_index: int
    ) -> Dict:
        """Create a chunk dictionary for embedding."""
        return {
            "file_path": document.file_path,
            "title": document.title,
            "content": content.strip(),
            "chunk_index": chunk_index,
            "metadata": {
                "tags": document.tags,
                "links": document.links,
                "created_at": (
                    document.created_at.isoformat() if document.created_at else None
                ),
                "modified_at": (
                    document.modified_at.isoformat() if document.modified_at else None
                ),
                **document.metadata,
            },
        }
