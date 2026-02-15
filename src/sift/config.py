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
    ingest_queue_name: str = "ingest"
    scheduler_poll_interval_seconds: int = 30
    scheduler_batch_size: int = 200
    auth_session_cookie_name: str = "sift_session"
    auth_session_ttl_days: int = 30
    auth_cookie_secure: bool = False
    auto_create_tables: bool = False
    dev_seed_enabled: bool = False
    dev_seed_default_user_email: str = "dev@sift.dev"
    dev_seed_default_user_password: str = "devpassword123!"
    dev_seed_default_user_display_name: str = "Dev User"
    dev_seed_opml_path: str | None = None
    dev_seed_monitoring_folder_name: str = "Monitoring feeds"
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    plugin_paths: list[str] = Field(
        default_factory=lambda: [
            "sift.plugins.builtin.noop:NoopPlugin",
            "sift.plugins.builtin.keyword_heuristic_classifier:KeywordHeuristicClassifierPlugin",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

