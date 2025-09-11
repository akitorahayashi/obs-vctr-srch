async def test_api_health_check(client):
    """Test API health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_hello_world(client):
    """Test hello world endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
