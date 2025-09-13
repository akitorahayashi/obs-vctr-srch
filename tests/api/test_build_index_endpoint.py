import pytest
from fastapi.testclient import TestClient

import src.apps.api.router as router_module
from src.main import app


# Dummy SyncCoordinator to simulate behavior
class DummyGitManager:
    def __init__(self, repo=None):
        self.repo = repo


class DummySyncCoordinator:
    def __init__(self, repo_exists=False):
        # git_manager with repo attribute
        self.git_manager = DummyGitManager(repo=object() if repo_exists else None)
        self.vector_store = None

    def initial_setup(self):
        return {"success": True, "message": "initial setup called"}

    def full_sync(self):
        return {"success": True, "message": "full sync called"}


@pytest.fixture(autouse=True)
def override_get_sync_coordinator(monkeypatch):
    # Default dummy without repo (triggers initial_setup logic)
    monkeypatch.setattr(
        router_module,
        "get_sync_coordinator",
        lambda settings=None: DummySyncCoordinator(repo_exists=False),
    )
    yield
    monkeypatch.undo()


client = TestClient(app)


def test_build_index_initial_setup():
    response = client.post("/api/obs-vctr-srch/build-index")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "build-index complete"
    assert data["result"]["message"] == "initial setup called"


def test_build_index_rebuild(monkeypatch):
    # Override to simulate existing repo
    monkeypatch.setattr(
        router_module,
        "get_sync_coordinator",
        lambda settings=None: DummySyncCoordinator(repo_exists=True),
    )
    response = client.post("/api/obs-vctr-srch/build-index")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "build-index complete"
    assert data["result"]["message"] == "full sync called"
