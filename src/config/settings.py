from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class loads configuration values used throughout the application from
    environment variables. Since Docker Compose automatically loads the .env file
    from the project root, there's no need to explicitly specify the file path.
    """

    DATABASE_URL: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
