from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class FeedCreate(BaseModel):
    title: str
    url: HttpUrl
    site_url: HttpUrl | None = None


class FeedOut(BaseModel):
    id: UUID
    owner_id: UUID | None
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
    filtered_count: int = 0
    stream_match_count: int = 0
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


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(default="", max_length=255)


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OpmlImportEntryResult(BaseModel):
    url: str
    title: str
    status: Literal["created", "skipped_existing", "skipped_conflict", "invalid", "duplicate_in_file"]
    reason: str | None = None


class OpmlImportResult(BaseModel):
    total_entries: int = 0
    unique_urls: int = 0
    created_count: int = 0
    skipped_existing_count: int = 0
    skipped_conflict_count: int = 0
    invalid_count: int = 0
    duplicate_in_file_count: int = 0
    results: list[OpmlImportEntryResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class IngestRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_active: bool = True
    priority: int = Field(default=100, ge=0, le=10000)
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    source_contains: str | None = Field(default=None, max_length=1000)
    language_equals: str | None = Field(default=None, max_length=32)
    action: Literal["drop"] = "drop"


class IngestRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10000)
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    source_contains: str | None = Field(default=None, max_length=1000)
    language_equals: str | None = Field(default=None, max_length=32)
    action: Literal["drop"] | None = None


class IngestRuleOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    is_active: bool
    priority: int
    include_keywords: list[str]
    exclude_keywords: list[str]
    source_contains: str | None
    language_equals: str | None
    action: Literal["drop"]
    created_at: datetime
    updated_at: datetime


class KeywordStreamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True
    priority: int = Field(default=100, ge=0, le=10000)
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    source_contains: str | None = Field(default=None, max_length=1000)
    language_equals: str | None = Field(default=None, max_length=32)


class KeywordStreamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10000)
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    source_contains: str | None = Field(default=None, max_length=1000)
    language_equals: str | None = Field(default=None, max_length=32)


class KeywordStreamOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    is_active: bool
    priority: int
    include_keywords: list[str]
    exclude_keywords: list[str]
    source_contains: str | None
    language_equals: str | None
    created_at: datetime
    updated_at: datetime


class StreamArticleOut(BaseModel):
    matched_at: datetime
    article: ArticleOut

