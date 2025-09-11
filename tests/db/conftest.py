import os
import subprocess
import time
from typing import AsyncGenerator, Generator, Optional

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from alembic.config import Config
from src.db.database import create_db_session
from src.main import app

# Load environment variables from .env file
load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def db_setup(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Generator[str, None, None]:
    """
    Session-scoped fixture to manage the test database using docker-compose.

    This fixture is automatically used by all tests in this directory and its
    subdirectories. It handles xdist by having the master node start the DB
    container and share its connection URL with worker nodes via a temporary file.
    """
    is_master = not hasattr(request.config, "workerinput")

    db_conn_file = None
    if request.config.pluginmanager.is_registered("xdist"):
        # In xdist, tmp_path_factory provides a shared directory for the session.
        root_tmp_dir = tmp_path_factory.getbasetemp().parent
        db_conn_file = root_tmp_dir / "db_url.txt"

    if is_master:
        # Determine if sudo should be used based on environment variable
        use_sudo = os.getenv("SUDO") == "true"
        docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

        # Set environment variables for Docker Compose
        os.environ["HOST_BIND_IP"] = os.getenv("HOST_BIND_IP", "127.0.0.1")
        os.environ["TEST_PORT"] = os.getenv("TEST_PORT", "8002")

        # Define compose commands for DB only
        compose_up_command = docker_command + [
            "compose",
            "-f",
            "docker-compose.yml",
            "-f",
            "docker-compose.test.override.yml",
            "--project-name",
            "fastapi-template-db-test",
            "up",
            "-d",
            "db",
        ]
        compose_down_command = docker_command + [
            "compose",
            "-f",
            "docker-compose.yml",
            "-f",
            "docker-compose.test.override.yml",
            "--project-name",
            "fastapi-template-db-test",
            "down",
            "--remove-orphans",
        ]

        print("\n🚀 Starting PostgreSQL test container with docker-compose...")

        try:
            subprocess.run(
                compose_up_command, check=True, timeout=300
            )  # 5 minutes timeout

            # Build database URL from environment variables
            postgres_user = os.getenv("POSTGRES_USER", "user")
            postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
            postgres_host = os.getenv("POSTGRES_HOST", "localhost")
            postgres_port = os.getenv("POSTGRES_PORT", "5432")
            postgres_db = os.getenv("POSTGRES_TEST_DB_NAME", "tmpl-api-test")

            db_url_value = f"postgresql+psycopg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
            os.environ["DATABASE_URL"] = db_url_value
            print(f"✅ PostgreSQL container started: {db_url_value}")

            # Wait for DB to be ready
            time.sleep(5)

            print("🔄 Running database migrations...")
            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", "alembic")
            alembic_cfg.set_main_option("sqlalchemy.url", db_url_value)
            command.upgrade(alembic_cfg, "head")
            print("✅ Database migrations completed!")

            if db_conn_file:
                db_conn_file.write_text(db_url_value)

        except subprocess.CalledProcessError:
            print("\n🛑 compose up failed; performing cleanup...")
            subprocess.run(compose_down_command, check=False)
            raise

    else:  # worker node
        if not db_conn_file:
            pytest.fail(
                "xdist is running but the db_conn_file path could not be determined."
            )

        timeout = 20
        start_time = time.time()
        while not db_conn_file.exists():
            if time.time() - start_time > timeout:
                pytest.fail(
                    f"Worker could not find db_url.txt after {timeout} seconds."
                )
            time.sleep(0.1)
        db_url_value = db_conn_file.read_text()

    yield db_url_value

    if is_master:
        # Determine if sudo should be used based on environment variable
        use_sudo = os.getenv("SUDO") == "true"
        docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

        compose_down_command = docker_command + [
            "compose",
            "-f",
            "docker-compose.yml",
            "-f",
            "docker-compose.test.override.yml",
            "--project-name",
            "fastapi-template-db-test",
            "down",
            "--remove-orphans",
        ]

        print("\n🛑 Stopping PostgreSQL test container...")
        subprocess.run(compose_down_command, check=False)
        if db_conn_file and db_conn_file.exists():
            db_conn_file.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def db_url(db_setup: str) -> str:
    """
    Fixture to provide the database URL to tests.
    It receives the URL from the session-scoped db_setup fixture.
    """
    return db_setup


@pytest.fixture
def db_session(db_url: str) -> Generator[Session, None, None]:
    """
    Provides a transactional scope for each test function.
    """
    engine: Optional[Engine] = None
    db: Optional[Session] = None
    try:
        engine = create_engine(db_url)
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )
        db = TestingSessionLocal()

        app.dependency_overrides[create_db_session] = lambda: db

        yield db
    finally:
        if db:
            db.rollback()
            db.close()
        if engine:
            engine.dispose()
        app.dependency_overrides.pop(create_db_session, None)


@pytest.fixture
async def client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx.AsyncClient instance that is properly configured for
    database-dependent tests.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
