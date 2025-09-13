import os
import time
from typing import Generator

import httpx
import pytest
from dotenv import load_dotenv
from testcontainers.compose import DockerCompose

# Load environment variables from .env file
load_dotenv()

# Set environment variables for Docker Compose
os.environ["HOST_BIND_IP"] = os.getenv("HOST_BIND_IP", "127.0.0.1")
os.environ["TEST_PORT"] = os.getenv("TEST_PORT", "8005")


@pytest.fixture(scope="session", autouse=True)
def e2e_setup() -> Generator[None, None, None]:
    """
    Manages the lifecycle of the application for end-to-end testing using testcontainers.
    """
    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8005")
    health_url = f"http://{host_bind_ip}:{host_port}/health"

    # Initialize Docker Compose with testcontainers and isolated project name via env var
    test_project_name = os.getenv("TEST_PROJECT_NAME", "obs-vctr-srch-test")
    os.environ["COMPOSE_PROJECT_NAME"] = test_project_name
    compose = DockerCompose(
        ".",
        compose_file_name=["docker-compose.yml", "docker-compose.test.override.yml"],
    )

    try:
        # Start the containers
        compose.start()

        # Health Check
        start_time = time.time()
        timeout = 120  # 2 minutes for API startup including potential build
        is_healthy = False
        while time.time() - start_time < timeout:
            try:
                response = httpx.get(health_url, timeout=5)
                if response.status_code == 200:
                    print("✅ API is healthy!")
                    # Also check if obs endpoints are available
                    obs_health_url = (
                        f"http://{host_bind_ip}:{host_port}/api/obs-vctr-srch/health"
                    )
                    try:
                        obs_response = httpx.get(obs_health_url, timeout=5)
                        print(
                            f"🔍 /api/obs-vctr-srch/health response: {obs_response.status_code}"
                        )
                        if obs_response.status_code == 200:
                            print("✅ Obs endpoints are ready!")
                            is_healthy = True
                            break
                        else:
                            print(
                                f"⏳ Obs endpoints not ready yet, response: {obs_response.status_code}"
                            )
                            # Try to get more info about the error
                            print(f"Response content: {obs_response.text}")
                    except Exception as obs_e:
                        print(f"❌ Error checking obs endpoint: {obs_e}")
            except httpx.RequestError as e:
                print(
                    f"⏳ API not yet healthy, retrying... URL: {health_url}, Error: {e}"
                )
            time.sleep(3)

        if not is_healthy:
            print("\n🛑 Stopping E2E services due to health check failure...")
            compose.stop()
            pytest.fail(f"API did not become healthy within {timeout} seconds.")

        yield

    except Exception as e:
        print(f"\n🛑 Failed to start services: {e}")
        compose.stop()
        raise
    finally:
        # Stop services
        print("\n🛑 Stopping E2E services...")
        compose.stop()
