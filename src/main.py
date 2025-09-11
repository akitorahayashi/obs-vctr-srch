from fastapi import FastAPI

from src.api import router

app = FastAPI(
    title="Obsidian Vector Search API",
    version="0.1.0",
    description="A FastAPI application for searching Obsidian vault with vector embeddings",
)

# Include routers
app.include_router(router.router, prefix="/api")


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
