# API Endpoints

This API provides endpoints for searching and maintaining a synchronized vector index of an Obsidian vault. All application-specific endpoints are prefixed with `/api/obs-vctr-srch`.

## Health Check
- **GET /health**
  - **Description**: Global health check for the API server.
  - **Response**: 
    ```json
    {"status": "ok"}
    ```

- **GET /api/obs-vctr-srch/health**
  - **Description**: Health check specifically for obs-vctr-srch endpoints.
  - **Response**: 
    ```json
    {"status": "obs endpoints available"}
    ```

## Status
- **GET /api/obs-vctr-srch/status**
  - **Description**: Gets the current status of repository and vector store.
  - **Response**: 
    ```json
    {
      "sync_status": "ready",
      "repository": {"status": "available"},
      "vector_store": {"status": "available"}
    }
    ```

## Search
- **POST /api/obs-vctr-srch/search**
  - **Description**: Performs a vector search against the indexed documents.
  - **Request Body**:
    ```json
    {
      "query": "your search query",
      "n_results": 10,
      "file_filter": "optional/path/filter",
      "tag_filter": ["tag1", "tag2"]
    }
    ```
    - `query` (required): The search query string
    - `n_results` (optional, default: 10): Number of results to return
    - `file_filter` (optional): Filter results by file path pattern
    - `tag_filter` (optional): Filter results by tags
  - **Response**: Array of search result objects:
    ```json
    [
      {
        "id": "unique_chunk_id",
        "content": "matching text content",
        "distance": 0.123,
        "file_path": "path/to/note.md",
        "title": "Note Title",
        "chunk_index": 0,
        "tags": ["tag1", "tag2"],
        "links": ["[[linked note]]"],
        "created_at": "2023-01-01T00:00:00Z",
        "modified_at": "2023-01-02T00:00:00Z"
      }
    ]
    ```

## Index Management
- **POST /api/obs-vctr-srch/sync**
  - **Description**: Performs an incremental synchronization. Scans for changes in the repository (based on Git history) and updates the index with new, modified, or deleted notes.
  - **Query Parameters**:
    - `full_sync` (optional, default: false): Perform full sync instead of incremental
  - **Response**: 
    ```json
    {"status": "sync would happen", "full_sync": false}
    ```

  - **POST /api/obs-vctr-srch/build-index**
  - **Description**: Builds or rebuilds the search index by clearing any existing index and re-indexing all notes. If an index exists, it will be deleted before rebuilding; otherwise, a fresh index is created.
  - **Request Body**: None
  - **Response**:
    ```json
    {
      "status": "build-index complete",
      "result": {
        "success": true,
        "message": "Processed X files, Y failed",
        "stats": { /* detailed stats */ }
      }
    }
    ```

- **POST /api/obs-vctr-srch/reindex/{file_path}**
  - **Description**: Forces re-indexing of a specific file.
  - **Path Parameters**:
    - `file_path`: The path to the file to re-index (can contain slashes)
  - **Response**: 
    ```json
    {"status": "reindex would happen", "file_path": "path/to/file.md"}
    ```
