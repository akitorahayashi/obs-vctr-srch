import importlib.util
import sys
from pathlib import Path

from fastapi import Depends, FastAPI

from src.apps.api import router
from src.apps.api.router import get_git_manager as router_get_git_manager
from src.config.settings import Settings, get_settings
from src.models import GitManager
from src.protocols.git_manager_protocol import GitManagerProtocol

settings = get_settings()

# --- 依存性定義 ---


def get_real_git_manager(
    settings: Settings = Depends(get_settings),
) -> GitManagerProtocol:
    """本番用のGitManagerを返します。"""
    print("🌐 Production mode: Using real GitManager")
    return GitManager(
        repo_url=settings.OBSIDIAN_REPO_URL,
        local_path=settings.OBSIDIAN_LOCAL_PATH,
        branch=settings.OBSIDIAN_BRANCH,
        github_token=settings.OBS_VAULT_TOKEN,
    )


def get_mock_git_manager(
    settings: Settings = Depends(get_settings),
) -> GitManagerProtocol:
    """デバッグ用のMockGitManagerを返します。"""
    # モックは main.py のDEBUGブロック内でインポートされます
    from mocks.git_manager import MockGitManager

    print("🔧 DEBUG mode: Using MockGitManager (via DI Override)")
    return MockGitManager(
        repo_url=settings.OBSIDIAN_REPO_URL,
        local_path=settings.OBSIDIAN_LOCAL_PATH,
        branch=settings.OBSIDIAN_BRANCH,
        github_token=settings.OBS_VAULT_TOKEN,
    )


# --- アプリケーション初期化 ---

app = FastAPI(
    title="Obsidian Vector Search API",
    version="0.1.0",
    description="A FastAPI application for searching Obsidian vault with vector embeddings",
)

# --- DEBUG設定に基づきDIの上書きを設定 ---

if settings.DEBUG:
    dev_path = Path(__file__).parent.parent / "dev"
    if dev_path.exists():
        sys.path.append(str(dev_path))
        print("🔧 'dev' directory added to sys.path for mock imports.")
        # Use importlib to check if MockGitManager is available
        if importlib.util.find_spec("mocks.git_manager") is not None:
            app.dependency_overrides[get_real_git_manager] = get_mock_git_manager
        else:
            print("⚠️ MockGitManager not found, falling back to real GitManager.")
    else:
        print("⚠️ 'dev' directory not found. Using real GitManager.")

# Include routers after dependency overrides are set
app.include_router(router.router, prefix="/api")

# Override the router's get_git_manager with our dependency function
# Use importlib to determine whether to override with mock or real
if settings.DEBUG and importlib.util.find_spec("mocks.git_manager") is not None:
    app.dependency_overrides[router_get_git_manager] = get_mock_git_manager
else:
    app.dependency_overrides[router_get_git_manager] = get_real_git_manager

# Include routers
app.include_router(router.router, prefix="/api")


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
