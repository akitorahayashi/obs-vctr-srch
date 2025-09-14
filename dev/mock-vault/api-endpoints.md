# API Endpoints Documentation

The obs-vctr-srch application exposes several REST endpoints for managing and searching your Obsidian vault.

## Health Check

- `GET /health` - Returns application health status
- `GET /api/obs-vctr-srch/health` - Vector search service health

## Repository Management

- `GET /api/obs-vctr-srch/status` - Get repository and vector store status
- `POST /api/obs-vctr-srch/sync` - Synchronize with remote repository
- `POST /api/obs-vctr-srch/build-index` - Rebuild vector index from scratch

## Search Operations

- `POST /api/obs-vctr-srch/search` - Perform semantic search
  - Request body: `{"query": "your search terms", "n_results": 5}`
  - Returns: JSON with matching documents and similarity scores

## Admin Interface

The admin dashboard is available on port 8010 and provides a web interface for monitoring system status and triggering operations.