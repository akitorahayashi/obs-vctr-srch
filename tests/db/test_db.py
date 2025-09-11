from sqlalchemy import text
from sqlalchemy.orm import Session


def test_db_connection(db_session: Session):
    """Smoke test for database connection using conftest fixture."""
    result = db_session.execute(text("SELECT 1")).fetchone()
    assert result[0] == 1


def test_db_version(db_session: Session):
    """Smoke test to check PostgreSQL version using conftest fixture."""
    result = db_session.execute(text("SELECT version()")).fetchone()
    version = result[0]
    assert "PostgreSQL" in version


async def test_api_health_check(client):
    """Test API health check endpoint with database connection."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
