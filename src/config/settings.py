from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class loads configuration values used throughout the application from
    environment variables. Since Docker Compose automatically loads the .env file
    from the project root, there's no need to explicitly specify the file path.
    """

    # Obsidian Vector Search settings
    OBSIDIAN_REPO_URL: str = "https://github.com/akitorahayashi/obsidian-vault.git"
    OBSIDIAN_LOCAL_PATH: str = "./obsidian-vault"
    OBSIDIAN_BRANCH: str = "main"
    VECTOR_DB_PATH: str = "./chroma_db"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    GITHUB_TOKEN: str = ""  # For private repositories


@lru_cache
def get_settings() -> Settings:
    return Settings()
