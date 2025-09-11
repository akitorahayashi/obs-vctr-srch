from fastapi import FastAPI

app = FastAPI(
    title="FastAPI Template",
    version="0.1.0",
    description="A FastAPI template project",
)


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
