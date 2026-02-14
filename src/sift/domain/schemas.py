from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class FeedCreate(BaseModel):
    title: str
    url: HttpUrl
    site_url: HttpUrl | None = None


class FeedOut(BaseModel):
    id: UUID
    title: str
    url: str
    site_url: str | None
    is_active: bool
    fetch_interval_minutes: int
    etag: str | None
    last_modified: str | None
    last_fetched_at: datetime | None
    last_fetch_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeedIngestResult(BaseModel):
    feed_id: UUID
    fetched_count: int = 0
    inserted_count: int = 0
    duplicate_count: int = 0
    plugin_processed_count: int = 0
    errors: list[str] = Field(default_factory=list)


class ArticleOut(BaseModel):
    id: UUID
    feed_id: UUID | None
    source_id: str
    canonical_url: str | None
    title: str
    content_text: str
    language: str | None
    published_at: datetime | None
    duplicate_of_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KeywordFilterPreviewRequest(BaseModel):
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)

