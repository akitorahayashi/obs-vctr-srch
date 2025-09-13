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
OBSIDIAN_REPO_URL=https://github.com/yourusername/your-obs-vault.git
OBS_VAULT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

Note: `OBSIDIAN_LOCAL_PATH`, `OBSIDIAN_BRANCH`, and `VECTOR_DB_PATH` are now hardcoded in the settings.

#### GitHub Personal Access Token Setup

1. **Create Token**: Go to [GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)

2. **Generate new token**: Click "Generate new token (classic)"

3. **Configure token**:
   - **Note**: `Obsidian Vault Access` (or any descriptive name)
   - **Expiration**: Choose appropriate expiration (90 days recommended)
   - **Scopes**: Select the following permissions:

4. **For private repositories** (recommended scope):
   - ✅ **repo** - Full control of private repositories
   
5. **For public repositories only** (minimal scope):
   - ✅ **public_repo** - Access public repositories

6. **Copy token**: After creation, copy the token immediately (it won't be shown again)

7. **Add to .env**: Paste the token as `OBS_VAULT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### Security Notes
- ⚠️ **Never commit** the `.env` file with real tokens
- 🔄 **Rotate tokens** regularly (every 90 days)
- 🔒 **Use minimal scopes** - only `public_repo` if your vault is public
- 📝 **Monitor token usage** in GitHub Settings → Developer settings

### 3. Start Development Server

```bash
make up
```

The API will be available at `http://127.0.0.1:8000` (configurable in `.env`).

**Note**: Initial synchronization runs automatically on first startup. The API will be ready to use once the sync completes.

## API Documentation

API endpoint documentation is available in [`src/api/README.md`](src/api/README.md).

Interactive API documentation is available when the server is running:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

## Development Commands

| Command | Description |
|---------|-------------|
| `make setup` | Initialize environment files |
| `make up` | Start development containers |
| `make down` | Stop development containers |
| `make test` | Run all tests |
| `make unit-test` | Run unit tests only |
| `make intg-test` | Run integration tests only |
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
├── api/              # API endpoints and router
├── services/         # Business logic services
├── config/           # Configuration
├── db/               # Database models
├── middlewares/      # Custom middleware
└── main.py          # FastAPI application

tests/
├── unit/            # Unit tests (TestClient)
├── intg/            # Integration tests
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
- **Integration Tests**: API endpoint tests  
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