"""initial schema

Revision ID: 20260214_0001
Revises:
Create Date: 2026-02-14 19:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260214_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feeds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("site_url", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("fetch_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("etag", sa.String(length=512), nullable=True),
        sa.Column("last_modified", sa.String(length=512), nullable=True),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_fetch_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feeds_url"), "feeds", ["url"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("feed_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["feeds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "feed_id", name="uq_subscription_user_feed"),
    )
    op.create_index(op.f("ix_subscriptions_feed_id"), "subscriptions", ["feed_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=False)

    op.create_table(
        "raw_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("feed_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.String(length=1024), nullable=False),
        sa.Column("source_guid", sa.String(length=1024), nullable=True),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["feeds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_id", "source_id", name="uq_raw_entry_feed_source"),
    )
    op.create_index(op.f("ix_raw_entries_feed_id"), "raw_entries", ["feed_id"], unique=False)
    op.create_index(op.f("ix_raw_entries_source_guid"), "raw_entries", ["source_guid"], unique=False)
    op.create_index(op.f("ix_raw_entries_source_id"), "raw_entries", ["source_id"], unique=False)
    op.create_index(op.f("ix_raw_entries_source_url"), "raw_entries", ["source_url"], unique=False)

    op.create_table(
        "articles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("feed_id", sa.UUID(), nullable=True),
        sa.Column("source_id", sa.String(length=1024), nullable=False),
        sa.Column("canonical_url", sa.String(length=2000), nullable=True),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duplicate_of_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["duplicate_of_id"], ["articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["feed_id"], ["feeds.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_id", "source_id", name="uq_article_feed_source"),
    )
    op.create_index(op.f("ix_articles_canonical_url"), "articles", ["canonical_url"], unique=False)
    op.create_index(op.f("ix_articles_duplicate_of_id"), "articles", ["duplicate_of_id"], unique=False)
    op.create_index(op.f("ix_articles_feed_id"), "articles", ["feed_id"], unique=False)
    op.create_index(op.f("ix_articles_language"), "articles", ["language"], unique=False)
    op.create_index(op.f("ix_articles_published_at"), "articles", ["published_at"], unique=False)
    op.create_index(op.f("ix_articles_source_id"), "articles", ["source_id"], unique=False)

    op.create_table(
        "article_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("is_starred", sa.Boolean(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "article_id", name="uq_article_state_user_article"),
    )
    op.create_index(op.f("ix_article_states_article_id"), "article_states", ["article_id"], unique=False)
    op.create_index(op.f("ix_article_states_is_archived"), "article_states", ["is_archived"], unique=False)
    op.create_index(op.f("ix_article_states_is_read"), "article_states", ["is_read"], unique=False)
    op.create_index(op.f("ix_article_states_is_starred"), "article_states", ["is_starred"], unique=False)
    op.create_index(op.f("ix_article_states_user_id"), "article_states", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_article_states_user_id"), table_name="article_states")
    op.drop_index(op.f("ix_article_states_is_starred"), table_name="article_states")
    op.drop_index(op.f("ix_article_states_is_read"), table_name="article_states")
    op.drop_index(op.f("ix_article_states_is_archived"), table_name="article_states")
    op.drop_index(op.f("ix_article_states_article_id"), table_name="article_states")
    op.drop_table("article_states")

    op.drop_index(op.f("ix_articles_source_id"), table_name="articles")
    op.drop_index(op.f("ix_articles_published_at"), table_name="articles")
    op.drop_index(op.f("ix_articles_language"), table_name="articles")
    op.drop_index(op.f("ix_articles_feed_id"), table_name="articles")
    op.drop_index(op.f("ix_articles_duplicate_of_id"), table_name="articles")
    op.drop_index(op.f("ix_articles_canonical_url"), table_name="articles")
    op.drop_table("articles")

    op.drop_index(op.f("ix_raw_entries_source_url"), table_name="raw_entries")
    op.drop_index(op.f("ix_raw_entries_source_id"), table_name="raw_entries")
    op.drop_index(op.f("ix_raw_entries_source_guid"), table_name="raw_entries")
    op.drop_index(op.f("ix_raw_entries_feed_id"), table_name="raw_entries")
    op.drop_table("raw_entries")

    op.drop_index(op.f("ix_subscriptions_user_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_feed_id"), table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index(op.f("ix_feeds_url"), table_name="feeds")
    op.drop_table("feeds")
