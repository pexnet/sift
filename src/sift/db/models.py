import uuid
from datetime import UTC, datetime

from sqlalchemy import UUID, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sift.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FeedFolder(TimestampMixin, Base):
    __tablename__ = "feed_folders"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_feed_folders_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    sort_order: Mapped[int] = mapped_column(Integer, default=100, index=True)


class Feed(TimestampMixin, Base):
    __tablename__ = "feeds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("feed_folders.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True, index=True)
    site_url: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    fetch_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    etag: Mapped[str | None] = mapped_column(String(512))
    last_modified: Mapped[str | None] = mapped_column(String(512))
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_fetch_error: Mapped[str | None] = mapped_column(String(1000))


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "feed_id", name="uq_subscription_user_feed"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    feed_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feeds.id", ondelete="CASCADE"), index=True)


class RawEntry(TimestampMixin, Base):
    __tablename__ = "raw_entries"
    __table_args__ = (UniqueConstraint("feed_id", "source_id", name="uq_raw_entry_feed_source"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feed_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feeds.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    source_guid: Mapped[str | None] = mapped_column(String(1024), index=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class Article(TimestampMixin, Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("feed_id", "source_id", name="uq_article_feed_source"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feed_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feeds.id", ondelete="SET NULL"), nullable=True, index=True)
    source_id: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    canonical_url: Mapped[str | None] = mapped_column(String(2000), index=True)
    canonical_url_normalized: Mapped[str | None] = mapped_column(String(2000), index=True)
    content_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str | None] = mapped_column(String(32), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("articles.id", ondelete="SET NULL"), index=True)
    dedup_confidence: Mapped[float] = mapped_column(Float, default=1.0)


class ArticleState(TimestampMixin, Base):
    __tablename__ = "article_states"
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_article_state_user_article"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class AuthIdentity(TimestampMixin, Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_identity_provider_subject"),
        UniqueConstraint("user_id", "provider", name="uq_auth_identity_user_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_user_id: Mapped[str] = mapped_column(String(320), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(1024))
    metadata_json: Mapped[str | None] = mapped_column(Text)


class UserSession(TimestampMixin, Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))


class ApiToken(TimestampMixin, Base):
    __tablename__ = "api_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    scopes_json: Mapped[str] = mapped_column(Text, default="[]")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class IngestRule(TimestampMixin, Base):
    __tablename__ = "ingest_rules"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_ingest_rules_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    include_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    exclude_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    source_contains: Mapped[str | None] = mapped_column(String(1000))
    language_equals: Mapped[str | None] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(32), default="drop", index=True)


class KeywordStream(TimestampMixin, Base):
    __tablename__ = "keyword_streams"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_keyword_streams_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    match_query: Mapped[str | None] = mapped_column(Text)
    include_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    exclude_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    source_contains: Mapped[str | None] = mapped_column(String(1000))
    language_equals: Mapped[str | None] = mapped_column(String(32), index=True)
    classifier_mode: Mapped[str] = mapped_column(String(32), default="rules_only", index=True)
    classifier_plugin: Mapped[str | None] = mapped_column(String(128), index=True)
    classifier_min_confidence: Mapped[float] = mapped_column(Float, default=0.7)


class KeywordStreamMatch(Base):
    __tablename__ = "keyword_stream_matches"
    __table_args__ = (UniqueConstraint("stream_id", "article_id", name="uq_keyword_stream_matches_stream_article"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("keyword_streams.id", ondelete="CASCADE"), index=True)
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
