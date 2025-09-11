# Obsidian Vector Search API

A FastAPI application that enables vector-based search of your private Obsidian vault.

## Features

- **Git Repository Sync** - Clone and sync with private Obsidian vault repositories
- **Incremental Updates** - Only re-embed changed files using git diff detection
- **Vector Search** - Fast semantic search using sentence transformers and ChromaDB
- **Obsidian-Aware Processing** - Handles frontmatter, tags, internal links, and markdown
- **FastAPI** - Modern, fast web framework with automatic API documentation
- **Docker** - Containerized development and deployment

## Quick Start

### 1. Prerequisites

- **Docker** - For containerized deployment (optional)

### 2. Setup Environment

```bash
make setup
```

This installs dependencies with uv and creates `.env` file from `.env.example`.

Edit `.env` to configure your Obsidian repository:
```env
OBSIDIAN_REPO_URL=https://github.com/yourusername/your-obsidian-vault.git
OBSIDIAN_LOCAL_PATH=./obsidian-vault
OBSIDIAN_BRANCH=main
VECTOR_DB_PATH=./chroma_db
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

### 3. Start Development Server

```bash
make up
```

The API will be available at `http://127.0.0.1:8000` (configurable in `.env`).

### 4. Initialize Your Vault

```bash
# Setup repository and perform initial sync
curl -X POST "http://127.0.0.1:8000/api/v1/obsidian/setup"
```

## API Endpoints

### Core Endpoints
- `GET /` - Hello World
- `GET /health` - Health check

### Obsidian Vault Management
- `POST /api/v1/obsidian/setup` - Initialize repository and perform initial sync
- `POST /api/v1/obsidian/sync` - Incremental or full synchronization
- `POST /api/v1/obsidian/search` - Vector search in your vault
- `GET /api/v1/obsidian/status` - Repository and vector store status
- `POST /api/v1/obsidian/cleanup` - Remove orphaned embeddings
- `GET /api/v1/obsidian/stats` - Vector store statistics


## Development Commands

| Command | Description |
|---------|-------------|
| `make setup` | Initialize environment files |
| `make up` | Start development containers |
| `make down` | Stop development containers |
| `make test` | Run all tests |
| `make unit-test` | Run unit tests only |
| `make db-test` | Run database tests only |
| `make e2e-test` | Run end-to-end tests only |
| `make format` | Format code with Black and fix with Ruff |
| `make lint` | Check code format and lint |
| `make shell` | Open shell in API container |
| `make logs` | View API container logs |
| `make migrate` | Run database migrations |
| `make migration m="msg"` | Generate a new database migration |

## Project Structure

```
src/
├── api/v1/           # API version 1
├── config/           # Configuration
├── db/               # Database models
├── middlewares/      # Custom middleware
└── main.py          # FastAPI application

tests/
├── unit/            # Unit tests (TestClient)
├── db/              # Database tests (testcontainers)
└── e2e/             # End-to-end tests (testcontainers + HTTP)

alembic/             # Database migrations
```

## Environment Variables

Configure in `.env`:

- `PROJECT_NAME` - Project name for Docker volumes (default: fastapi-tmpl)
- `HOST_BIND_IP` - IP to bind (default: 127.0.0.1)
- `HOST_PORT` - Port to bind (default: 8000)
- `DEV_PORT` - Development port (default: 8001)
- `TEST_PORT` - Test port (default: 8002)
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_HOST_DB_NAME` - Production database name
- `POSTGRES_DEV_DB_NAME` - Development database name
- `POSTGRES_TEST_DB_NAME` - Test database name

## Testing

The project includes three types of tests:

- **Unit Tests**: Fast tests using FastAPI TestClient
- **Database Tests**: PostgreSQL integration tests using testcontainers
- **E2E Tests**: Full stack tests using Docker Compose via testcontainers

All tests run independently without external dependencies.

## Deployment

### Production

```bash
make up-prod
```

Uses production environment configuration from `.env`.

## Docker Architecture

The project uses a sophisticated 5-stage multi-stage Docker build optimized for uv:

### Build Stages

1. **`base`** - Foundation stage with uv installation and dependency files
   - Installs uv package manager
   - Copies `pyproject.toml`, `uv.lock`, and `README.md`
   - Shared base for dependency installation stages

2. **`dev-deps`** - Development dependencies
   - Extends base stage
   - Installs system tools (curl for debugging)
   - Runs `uv sync` to install all dependencies including dev dependencies
   - Creates complete virtual environment for development and testing

3. **`prod-deps`** - Production dependencies only
   - Extends base stage  
   - Runs `uv sync --no-dev` to install only production dependencies
   - Creates lean virtual environment for production

4. **`development`** - Development runtime environment
   - Based on fresh Python 3.12 slim image
   - Installs PostgreSQL client and development tools
   - Creates non-root user for security
   - Copies virtual environment from `dev-deps` stage
   - Includes all application code and development utilities
   - Suitable for local development and CI/CD testing

5. **`production`** - Production runtime environment  
   - Based on fresh Python 3.12 slim image
   - Minimal system dependencies (PostgreSQL client only)
   - Creates non-root user for security
   - Copies lean virtual environment from `prod-deps` stage
   - Includes only necessary application code
   - Optimized for production deployment

### Key Benefits

- **Fast Builds**: uv's speed combined with Docker layer caching
- **Security**: Non-root user execution in runtime stages
- **Optimization**: Separate dev/prod dependency trees
- **Caching**: Aggressive use of Docker build cache for dependencies
- **Minimal Attack Surface**: Production image contains only essential components

### Build Targets

```bash
# Build development image
docker build --target development -t myapp:dev .

# Build production image  
docker build --target production -t myapp:prod .

# Test build (validates production build without keeping image)
make build-test
```

## Adding Database Models

1. Create models in `src/db/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Apply migration: `alembic upgrade head`

Database migrations run automatically in Docker containers.

## Code Quality

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **uv**: Ultra-fast dependency management
- **Pytest**: Testing framework with testcontainers

Run `make format` and `make lint` before committing.

## Volume Management

Project volumes are prefixed with `PROJECT_NAME` to avoid conflicts:

- `${PROJECT_NAME}-postgres-db-prod`: PostgreSQL data persistence
- Volumes are marked as `external: false` for proper cleanup
- Each environment (dev/prod/test) uses separate Docker Compose project names