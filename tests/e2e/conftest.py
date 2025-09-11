import os
import subprocess
import time
from typing import Generator

import httpx
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set environment variables for Docker Compose
os.environ["HOST_BIND_IP"] = os.getenv("HOST_BIND_IP", "127.0.0.1")
os.environ["TEST_PORT"] = os.getenv("TEST_PORT", "8002")


@pytest.fixture(scope="session", autouse=True)
def e2e_setup() -> Generator[None, None, None]:
    """
    Manages the lifecycle of the application for end-to-end testing.
    """
    # Determine if sudo should be used based on environment variable
    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8002")
    health_url = f"http://{host_bind_ip}:{host_port}/health"

    # Define compose commands
    compose_up_command = docker_command + [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        "fastapi-template-test",
        "up",
        "-d",
    ]
    compose_down_command = docker_command + [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        "fastapi-template-test",
        "down",
        "--remove-orphans",
    ]

    try:
        subprocess.run(compose_up_command, check=True, timeout=300)  # 5 minutes timeout

        # Health Check
        start_time = time.time()
        timeout = 120  # 2 minutes for basic API health check
        is_healthy = False
        while time.time() - start_time < timeout:
            try:
                response = httpx.get(health_url, timeout=5)
                if response.status_code == 200:
                    print("✅ API is healthy!")
                    is_healthy = True
                    break
            except httpx.RequestError as e:
                print(
                    f"⏳ API not yet healthy, retrying... URL: {health_url}, Error: {e}"
                )
            time.sleep(5)

        if not is_healthy:
            subprocess.run(
                docker_command
                + [
                    "compose",
                    "-f",
                    "docker-compose.yml",
                    "-f",
                    "docker-compose.test.override.yml",
                    "--project-name",
                    "fastapi-template-test",
                    "logs",
                    "api",
                ]
            )
            # Ensure teardown on health check failure
            print("\n🛑 Stopping E2E services due to health check failure...")
            subprocess.run(compose_down_command, check=False)
            pytest.fail(f"API did not become healthy within {timeout} seconds.")

        yield

    except subprocess.CalledProcessError as e:
        print("\n🛑 compose up failed; performing cleanup...")
        if hasattr(e, "stdout") and hasattr(e, "stderr"):
            print(f"Exit code: {e.returncode}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
        subprocess.run(compose_down_command, check=False)
        raise
    finally:
        # Stop services
        print("\n🛑 Stopping E2E services...")
        subprocess.run(compose_down_command, check=False)
