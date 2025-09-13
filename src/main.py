from fastapi import FastAPI

from src.apps.api import router

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
