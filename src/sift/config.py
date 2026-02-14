from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SIFT_", case_sensitive=False)

    env: str = "development"
    app_name: str = "Sift"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./sift.db"
    redis_url: str = "redis://localhost:6379/0"
    auto_create_tables: bool = True
    plugin_paths: list[str] = Field(default_factory=lambda: ["sift.plugins.builtin.noop:NoopPlugin"])


@lru_cache
def get_settings() -> Settings:
    return Settings()

