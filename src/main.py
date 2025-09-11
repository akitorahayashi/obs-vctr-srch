from fastapi import FastAPI

from src.api.v1.routers import obsidian

app = FastAPI(
    title="Obsidian Vector Search API",
    version="0.1.0",
    description="A FastAPI application for searching Obsidian vault with vector embeddings",
)

# Include routers
app.include_router(obsidian.router, prefix="/api/v1")


@app.get("/")
async def hello_world():
    """
    Hello World endpoint.
    """
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
