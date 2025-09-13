# API Endpoints

This API provides endpoints for searching and maintaining a synchronized vector index of an Obsidian vault. All application-specific endpoints are prefixed with `/api/obs-vctr-srch`.

## Health Check
- **GET /health**
  - **Description**: Checks if the API server is running and responsive. This endpoint is not prefixed.
  - **Response**: `{"status": "ok"}`

## Search
- **POST /api/obs-vctr-srch/search**
  - **Description**: Performs a vector search against the indexed documents.
  - **Request Body**:
    ```json
    {
      "query": "your search query",
      "n_results": 10
    }
    ```
  - **Response**: An array of search result objects.

## Index Management
- **POST /api/obs-vctr-srch/sync**
  - **Description**: Performs an incremental synchronization. It scans for changes in the `obs-vault` repository (based on Git history) and updates the index with new, modified, or deleted notes.
  - **Response**: A summary of the synchronization, e.g., `{"success": true, "stats": {"added": 5, "updated": 2, "deleted": 1}}`.

- **POST /api/obs-vctr-srch/rebuild**
  - **Description**: Completely rebuilds the search index. This is a destructive operation that first deletes all existing indexed data. It then re-scans the entire `obs-vault` and creates a new index based on the `EMBEDDING_MODEL_NAME` specified in the environment.
  - **Response**: A summary of the operation, e.g., `{"success": true, "message": "Index rebuilt successfully.", "stats": {"indexed_documents": 150}}`.
