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
os.environ["TEST_PORT"] = os.getenv("TEST_PORT", "8005")


@pytest.fixture(scope="session", autouse=True)
def e2e_setup() -> Generator[None, None, None]:
    """
    Manages the lifecycle of the application for end-to-end testing.
    """
    # Determine if sudo should be used based on environment variable
    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "-E", "docker"] if use_sudo else ["docker"]

    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8005")
    health_url = f"http://{host_bind_ip}:{host_port}/health"

    # Initialize Docker Compose project name
    test_project_name = os.getenv("TEST_PROJECT_NAME", "obs-vctr-srch-test")

    # Define compose commands
    compose_up_command = docker_command + [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        test_project_name,
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
        test_project_name,
        "down",
        "--remove-orphans",
    ]
    compose_logs_command = docker_command + [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        test_project_name,
        "logs",
    ]

    try:
        subprocess.run(
            compose_up_command, check=True, timeout=600, env=os.environ
        )  # 10 minutes timeout

        # Health Check
        start_time = time.time()
        timeout = 600  # 10 minutes for API startup including model download
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
            # Dump logs for debugging on health check failure
            print("\n📄 Dumping logs for debugging...")
            subprocess.run(compose_logs_command, check=False)
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
        # Dump logs for debugging
        print("\n📄 Dumping logs for debugging...")
        subprocess.run(compose_logs_command, check=False)
        # Stop services
        print("\n🛑 Stopping E2E services...")
        subprocess.run(compose_down_command, check=False)
