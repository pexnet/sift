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
    folder_id: UUID | None
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
    canonical_duplicate_count: int = 0
    filtered_count: int = 0
    stream_match_count: int = 0
    plugin_processed_count: int = 0
    errors: list[str] = Field(default_factory=list)


class FeedFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int = Field(default=100, ge=0, le=10000)


class FeedFolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = Field(default=None, ge=0, le=10000)


class FeedFolderOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeedFolderAssignmentUpdate(BaseModel):
    folder_id: UUID | None


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
    dedup_confidence: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArticleListItemOut(BaseModel):
    id: UUID
    feed_id: UUID | None
    feed_title: str | None
    title: str
    canonical_url: str | None
    published_at: datetime | None
    created_at: datetime
    is_read: bool
    is_starred: bool
    is_archived: bool
    stream_ids: list[UUID] = Field(default_factory=list)


class ArticleDetailOut(BaseModel):
    id: UUID
    feed_id: UUID | None
    feed_title: str | None
    source_id: str
    canonical_url: str | None
    title: str
    content_text: str
    language: str | None
    published_at: datetime | None
    created_at: datetime
    is_read: bool
    is_starred: bool
    is_archived: bool
    stream_ids: list[UUID] = Field(default_factory=list)


class ArticleStatePatch(BaseModel):
    is_read: bool | None = None
    is_starred: bool | None = None
    is_archived: bool | None = None


class ArticleStateBulkPatch(BaseModel):
    article_ids: list[UUID] = Field(min_length=1, max_length=500)
    is_read: bool | None = None
    is_starred: bool | None = None
    is_archived: bool | None = None


class ArticleStateOut(BaseModel):
    article_id: UUID
    is_read: bool
    is_starred: bool
    is_archived: bool


class ArticleListResponse(BaseModel):
    items: list[ArticleListItemOut]
    total: int
    limit: int
    offset: int


class NavigationFeedNodeOut(BaseModel):
    id: UUID
    title: str
    unread_count: int


class NavigationFolderNodeOut(BaseModel):
    id: UUID | None
    name: str
    unread_count: int
    feeds: list[NavigationFeedNodeOut] = Field(default_factory=list)


class NavigationStreamNodeOut(BaseModel):
    id: UUID
    name: str
    unread_count: int


class NavigationSystemNodeOut(BaseModel):
    key: Literal["all", "fresh", "saved", "archived", "recent"]
    title: str
    unread_count: int


class NavigationTreeOut(BaseModel):
    systems: list[NavigationSystemNodeOut]
    folders: list[NavigationFolderNodeOut]
    streams: list[NavigationStreamNodeOut]


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
    match_query: str | None = Field(default=None, max_length=5000)
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    source_contains: str | None = Field(default=None, max_length=1000)
    language_equals: str | None = Field(default=None, max_length=32)
    classifier_mode: Literal["rules_only", "classifier_only", "hybrid"] = "rules_only"
    classifier_plugin: str | None = Field(default=None, max_length=128)
    classifier_min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class KeywordStreamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10000)
    match_query: str | None = Field(default=None, max_length=5000)
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    source_contains: str | None = Field(default=None, max_length=1000)
    language_equals: str | None = Field(default=None, max_length=32)
    classifier_mode: Literal["rules_only", "classifier_only", "hybrid"] | None = None
    classifier_plugin: str | None = Field(default=None, max_length=128)
    classifier_min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class KeywordStreamOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    is_active: bool
    priority: int
    match_query: str | None
    include_keywords: list[str]
    exclude_keywords: list[str]
    source_contains: str | None
    language_equals: str | None
    classifier_mode: Literal["rules_only", "classifier_only", "hybrid"]
    classifier_plugin: str | None
    classifier_min_confidence: float
    created_at: datetime
    updated_at: datetime


class StreamArticleOut(BaseModel):
    matched_at: datetime
    article: ArticleOut

