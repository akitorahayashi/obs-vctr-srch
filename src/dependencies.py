from functools import lru_cache

from fastapi import Depends

from src.config.settings import Settings
from src.models import GitManager, ObsidianProcessor, VectorStore
from src.services import SyncCoordinator


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    return VectorStore(settings=settings)


def get_git_manager(settings: Settings = Depends(get_settings)) -> GitManager:
    return GitManager(settings=settings)


def get_obsidian_processor(
    settings: Settings = Depends(get_settings),
) -> ObsidianProcessor:
    return ObsidianProcessor(settings=settings)


# Service層は、先行するModel層のDI（Getter）に依存する
def get_sync_coordinator(
    git_manager: GitManager = Depends(get_git_manager),
    vector_store: VectorStore = Depends(get_vector_store),
    processor: ObsidianProcessor = Depends(get_obsidian_processor),
) -> SyncCoordinator:
    return SyncCoordinator(
        git_manager=git_manager, vector_store=vector_store, processor=processor
    )
