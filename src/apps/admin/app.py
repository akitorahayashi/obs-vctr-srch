"""
Admin app for managing Obsidian Vector Search operations.
This is a standalone tool for administrators to monitor and control build index operations.
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI(
    title="Obsidian Vector Search - Admin Console",
    description="Administrative tools for managing vector search operations",
    version="1.0.0"
)

# Get the directory containing this file
current_dir = Path(__file__).parent

# Mount static files
static_dir = current_dir / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# API base URL (configurable via environment)
API_BASE_URL = os.getenv("OBS_API_URL", "http://127.0.0.1:8005")


@app.get("/")
async def dashboard():
    """Main admin dashboard."""
    return {
        "message": "Admin Console is running",
        "api_base_url": API_BASE_URL,
        "endpoints": [
            "/api/status",
            "/api/repository-status",
            "/build-index-monitor (coming soon)"
        ]
    }


@app.get("/build-index-monitor")
async def build_index_monitor():
    """Build index monitoring page."""
    return {
        "message": "Build index monitor endpoint",
        "streaming_url": f"{API_BASE_URL}/api/obs-vctr-srch/build-index-stream",
        "note": "Use a proper SSE client to monitor build progress"
    }


@app.get("/api/status")
async def get_api_status():
    """Check if the main API is accessible."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                # Also check obs health
                obs_response = await client.get(f"{API_BASE_URL}/api/obs-vctr-srch/health", timeout=5.0)
                return {
                    "status": "healthy",
                    "api_health": response.json(),
                    "obs_health": obs_response.json() if obs_response.status_code == 200 else None,
                    "api_url": API_BASE_URL
                }
            else:
                return {"status": "unhealthy", "api_url": API_BASE_URL}
    except Exception as e:
        return {"status": "error", "error": str(e), "api_url": API_BASE_URL}


@app.get("/api/repository-status")
async def get_repository_status():
    """Get repository status from the main API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/obs-vctr-srch/status", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API returned status code {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("ADMIN_HOST", "0.0.0.0")
    port = int(os.getenv("ADMIN_PORT", "8010"))
    
    print(f"Starting Obsidian Vector Search Admin Console on {host}:{port}")
    print(f"Main API URL: {API_BASE_URL}")
    
    # Only enable reload in development environment
    reload = os.getenv("ENVIRONMENT", "production") == "development"
    uvicorn.run(app, host=host, port=port, reload=reload)