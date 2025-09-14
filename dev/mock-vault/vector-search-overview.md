# Obsidian Vector Search System

This application provides semantic search capabilities for Obsidian vault contents using vector embeddings.

## Key Features

- **Semantic Search**: Find documents by meaning, not just keywords
- **FastAPI Backend**: High-performance REST API with automatic documentation
- **Admin Dashboard**: Web interface for monitoring and management
- **Docker Support**: Containerized deployment with docker-compose

## Architecture

The system uses sentence transformers to create embeddings of markdown documents, storing them in a vector database for fast similarity search.

Search queries are embedded using the same model and matched against document vectors to find the most relevant content.

## Usage

Access the API at `/api/obs-vctr-srch/search` with a JSON payload containing your query string.