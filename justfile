# ==============================================================================
# justfile for obs-vctr-srch Project Automation
# ==============================================================================

PROJECT_NAME := env("PROJECT_NAME", "obs-vctr-srch")

DEV_PROJECT_NAME := PROJECT_NAME + "-dev"
PROD_PROJECT_NAME := PROJECT_NAME + "-prod"
TEST_PROJECT_NAME := PROJECT_NAME + "-test"

DEV_COMPOSE  := "docker compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name " + DEV_PROJECT_NAME
PROD_COMPOSE := "docker compose -f docker-compose.yml --project-name " + PROD_PROJECT_NAME
TEST_COMPOSE := "docker compose -f docker-compose.yml -f docker-compose.test.override.yml --project-name " + TEST_PROJECT_NAME

# Show available recipes
help:
    @echo "Usage: just [recipe]"
    @echo "Available recipes:"
    @just --list | tail -n +2 | awk '{printf "  \033[36m%-20s\033[0m %s\n", $1, substr($0, index($0, $2))}'

default: help

# ==============================================================================
# Environment Setup
# ==============================================================================

# Initialize project: install dependencies, create .env file
setup:
    @echo "Installing python dependencies with uv..."
    @uv sync
    @echo "Creating environment file..."
    @if [ ! -f .env ] && [ -f .env.example ]; then \
        echo "Creating .env from .env.example..."; \
        cp .env.example .env; \
        echo "✅ Environment file created (.env)"; \
    else \
        echo ".env already exists. Skipping creation."; \
    fi
    @echo "💡 You can customize .env for your specific needs:"
    @echo "   📝 Change OLLAMA_HOST to switch between container/host Ollama"
    @echo "   📝 Adjust other settings as needed"

# ==============================================================================
# Development Environment Commands
# ==============================================================================

# Start all development containers in detached mode
up:
    @echo "Starting up development services..."
    @{{DEV_COMPOSE}} up -d

# Stop and remove all development containers
down:
    @echo "Shutting down development services..."
    @{{DEV_COMPOSE}} down --remove-orphans

# Start all production-like containers
up-prod:
    @echo "Starting up production-like services..."
    @{{PROD_COMPOSE}} up -d --build --pull always --remove-orphans

# Stop and remove all production-like containers
down-prod:
    @echo "Shutting down production-like services..."
    @{{PROD_COMPOSE}} down --remove-orphans

# View the logs for the development API service
logs:
    @echo "Following logs for the dev api service..."
    @{{DEV_COMPOSE}} logs -f api

# Open a shell inside the running development API container
shell:
    @echo "Opening shell in dev api container..."
    @{{DEV_COMPOSE}} exec api /bin/sh || (echo "Failed to open shell. Is the container running? Try 'just up'" && exit 1)

# Run database migrations against the development database
migrate:
    @echo "Running database migrations for dev environment..."
    @{{DEV_COMPOSE}} exec api sh -c ". /app/.venv/bin/activate && alembic upgrade head"

# Generate a new database migration file. Usage: just migration "Your migration message"
migration message:
    @echo "Generating new migration for dev environment with message: {{message}}..."
    @{{DEV_COMPOSE}} exec api sh -c ". /app/.venv/bin/activate && alembic revision --autogenerate -m \"{{message}}\""

# ==============================================================================
# CODE QUALITY
# ==============================================================================

# Format code with black and ruff --fix
format:
    @echo "Formatting code with black and ruff..."
    @uv run black .
    @uv run ruff check . --fix

# Lint code with black check and ruff
lint:
    @echo "Linting code with black check and ruff..."
    @uv run black --check .
    @uv run ruff check .

# ==============================================================================
# TESTING
# ==============================================================================

# Run the full test suite
test: unit-test intg-test build-test e2e-test

# Run the unit tests locally
unit-test:
    @echo "Running unit tests..."
    @uv run pytest tests/unit -v -s

# Run integration tests locally
intg-test:
    @echo "Running integration tests..."
    @uv run pytest tests/intg -v -s

# Run end-to-end tests against a live application stack
e2e-test:
    @echo "Running end-to-end tests..."
    @uv run pytest tests/e2e -v -s

# Build Docker image for testing without leaving artifacts
build-test:
    @echo "Building Docker image for testing (clean build)..."
    @TEMP_IMAGE_TAG=$(date +%s)-build-test; \
    docker build --target production --tag temp-build-test:$TEMP_IMAGE_TAG . && \
    echo "Build successful. Cleaning up temporary image..." && \
    docker rmi temp-build-test:$TEMP_IMAGE_TAG || true

# ==============================================================================
# CLEANUP
# ==============================================================================

# Remove __pycache__ and .venv to make project lightweight
clean:
    @echo "🧹 Cleaning up project..."
    @find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    @rm -rf .venv
    @rm -rf .pytest_cache
    @rm -rf .ruff_cache
    @echo "✅ Cleanup completed"