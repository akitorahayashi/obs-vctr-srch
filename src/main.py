import sys
from pathlib import Path

from fastapi import FastAPI

from src.apps.api import router
from src.config.settings import get_settings

settings = get_settings()

if settings.DEBUG:
    # Add dev path for mock implementations.
    # This allows importing from the 'dev/mocks' directory during development.
    dev_path = Path(__file__).parent.parent / "dev"
    if dev_path.exists():
        sys.path.append(str(dev_path))
        print(
            "🔧 Development mode: 'dev' directory added to sys.path for mock imports."
        )
    else:
        print("⚠️  'dev' directory not found. Mock imports might fail.")


app = FastAPI(
    title="Obsidian Vector Search API",
    version="0.1.0",
    description="A FastAPI application for searching Obsidian vault with vector embeddings",
)

# Include routers
app.include_router(router.router, prefix="/api")


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
