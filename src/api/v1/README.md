# API v1 Endpoints

This document describes the available endpoints for the Obsidian Vector Search API v1.

## Obsidian Vault Management

### Synchronization
- **POST /api/v1/obs/sync** - Incremental or full synchronization
  - Syncs your Obsidian vault with the vector database
  - Supports both incremental (only changed files) and full synchronization

### Search
- **POST /api/v1/obs/search** - Vector search in your vault
  - Performs semantic search across your Obsidian notes
  - Returns relevant notes based on vector similarity

### Status & Maintenance
- **GET /api/v1/obs/status** - Repository and vector store status
  - Shows current sync status, repository info, and database statistics
  
- **POST /api/v1/obs/cleanup** - Remove orphaned embeddings
  - Removes vector embeddings for files that no longer exist in the vault

- **POST /api/v1/obs/reindex/{file_path:path}** - Force re-indexing of a specific file
  - Forces re-indexing of a specific file in the vault

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

These interfaces allow you to test endpoints directly from your browser.