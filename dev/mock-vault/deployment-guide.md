# Deployment Configuration

This guide covers deployment options for the Obsidian Vector Search application.

## Environment Variables

Key configuration options in `.env`:

- `EMBEDDING_MODEL_NAME`: Sentence transformer model (default: all-mpnet-base-v2)
- `OBSIDIAN_REPO_URL`: GitHub repository URL for your vault
- `OBS_VAULT_TOKEN`: Personal access token for private repositories
- `BUILD_INDEX_TIMEOUT`: Maximum time for index building (default: 1800 seconds)

## Docker Compose

Run with `make up` for development or `make up-prod` for production deployment.

The system includes:
- API service on port 8000
- Admin interface on port 8010
- Automatic health checks and container restart policies

## Testing

Use `make e2e-test` to run the full test suite including:
- API health verification
- Search functionality testing
- Repository synchronization tests
- Admin interface integration

The test environment uses lightweight models for faster execution.