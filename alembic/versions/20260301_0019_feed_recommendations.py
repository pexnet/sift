"""add feed recommendations tables

Revision ID: 20260301_0019
Revises: 20260301_0018
Create Date: 2026-03-01 18:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260301_0019"
down_revision: str | None = "20260301_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RECOMMENDATIONS_TABLE = "feed_recommendations"
RECOMMENDATIONS_UNIQUE_USER_URL = "uq_feed_recommendations_user_url"
RECOMMENDATIONS_INDEX_USER_ID = "ix_feed_recommendations_user_id"
RECOMMENDATIONS_INDEX_STATUS = "ix_feed_recommendations_status"
RECOMMENDATIONS_INDEX_ACCEPTED_FEED_ID = "ix_feed_recommendations_accepted_feed_id"
RECOMMENDATIONS_INDEX_DECIDED_AT = "ix_feed_recommendations_decided_at"
RECOMMENDATIONS_INDEX_LAST_SEEN_AT = "ix_feed_recommendations_last_seen_at"
RECOMMENDATIONS_INDEX_USER_STATUS_CREATED = "ix_feed_recommendations_user_status_created"
RECOMMENDATIONS_STATUS_CHECK = "ck_feed_recommendations_status"

SOURCES_TABLE = "feed_recommendation_sources"
SOURCES_UNIQUE_RECOMMENDATION_STREAM = "uq_feed_recommendation_sources_recommendation_stream"
SOURCES_INDEX_RECOMMENDATION_ID = "ix_feed_recommendation_sources_recommendation_id"
SOURCES_INDEX_STREAM_ID = "ix_feed_recommendation_sources_discovery_stream_id"
SOURCES_INDEX_CREATED_AT = "ix_feed_recommendation_sources_created_at"
SOURCES_INDEX_STREAM_CREATED = "ix_feed_recommendation_sources_stream_created"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if RECOMMENDATIONS_TABLE not in table_names:
        op.create_table(
            RECOMMENDATIONS_TABLE,
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("feed_url", sa.String(length=2000), nullable=False),
            sa.Column("feed_url_normalized", sa.String(length=2000), nullable=False),
            sa.Column("feed_title", sa.String(length=1000), nullable=True),
            sa.Column("site_url", sa.String(length=2000), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("provider", sa.String(length=128), nullable=False),
            sa.Column("evidence_json", sa.Text(), nullable=True),
            sa.Column("accepted_feed_id", sa.UUID(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["accepted_feed_id"], ["feeds.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "feed_url_normalized", name=RECOMMENDATIONS_UNIQUE_USER_URL),
            sa.CheckConstraint(
                "status IN ('pending', 'accepted', 'denied', 'resolved_existing')",
                name=RECOMMENDATIONS_STATUS_CHECK,
            ),
        )
        op.create_index(RECOMMENDATIONS_INDEX_USER_ID, RECOMMENDATIONS_TABLE, ["user_id"], unique=False)
        op.create_index(RECOMMENDATIONS_INDEX_STATUS, RECOMMENDATIONS_TABLE, ["status"], unique=False)
        op.create_index(
            RECOMMENDATIONS_INDEX_ACCEPTED_FEED_ID,
            RECOMMENDATIONS_TABLE,
            ["accepted_feed_id"],
            unique=False,
        )
        op.create_index(RECOMMENDATIONS_INDEX_DECIDED_AT, RECOMMENDATIONS_TABLE, ["decided_at"], unique=False)
        op.create_index(RECOMMENDATIONS_INDEX_LAST_SEEN_AT, RECOMMENDATIONS_TABLE, ["last_seen_at"], unique=False)
        op.create_index(
            RECOMMENDATIONS_INDEX_USER_STATUS_CREATED,
            RECOMMENDATIONS_TABLE,
            ["user_id", "status", "created_at"],
            unique=False,
        )

    table_names = set(inspector.get_table_names())
    if SOURCES_TABLE not in table_names:
        op.create_table(
            SOURCES_TABLE,
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("recommendation_id", sa.UUID(), nullable=False),
            sa.Column("discovery_stream_id", sa.UUID(), nullable=False),
            sa.Column("provider_confidence", sa.Float(), nullable=True),
            sa.Column("evidence_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["recommendation_id"], ["feed_recommendations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["discovery_stream_id"], ["discovery_streams.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "recommendation_id",
                "discovery_stream_id",
                name=SOURCES_UNIQUE_RECOMMENDATION_STREAM,
            ),
        )
        op.create_index(SOURCES_INDEX_RECOMMENDATION_ID, SOURCES_TABLE, ["recommendation_id"], unique=False)
        op.create_index(SOURCES_INDEX_STREAM_ID, SOURCES_TABLE, ["discovery_stream_id"], unique=False)
        op.create_index(SOURCES_INDEX_CREATED_AT, SOURCES_TABLE, ["created_at"], unique=False)
        op.create_index(
            SOURCES_INDEX_STREAM_CREATED,
            SOURCES_TABLE,
            ["discovery_stream_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if SOURCES_TABLE in table_names:
        source_indexes = {index["name"] for index in inspector.get_indexes(SOURCES_TABLE)}
        if SOURCES_INDEX_STREAM_CREATED in source_indexes:
            op.drop_index(SOURCES_INDEX_STREAM_CREATED, table_name=SOURCES_TABLE)
        if SOURCES_INDEX_CREATED_AT in source_indexes:
            op.drop_index(SOURCES_INDEX_CREATED_AT, table_name=SOURCES_TABLE)
        if SOURCES_INDEX_STREAM_ID in source_indexes:
            op.drop_index(SOURCES_INDEX_STREAM_ID, table_name=SOURCES_TABLE)
        if SOURCES_INDEX_RECOMMENDATION_ID in source_indexes:
            op.drop_index(SOURCES_INDEX_RECOMMENDATION_ID, table_name=SOURCES_TABLE)
        op.drop_table(SOURCES_TABLE)

    table_names = set(inspector.get_table_names())
    if RECOMMENDATIONS_TABLE in table_names:
        recommendation_indexes = {index["name"] for index in inspector.get_indexes(RECOMMENDATIONS_TABLE)}
        if RECOMMENDATIONS_INDEX_USER_STATUS_CREATED in recommendation_indexes:
            op.drop_index(RECOMMENDATIONS_INDEX_USER_STATUS_CREATED, table_name=RECOMMENDATIONS_TABLE)
        if RECOMMENDATIONS_INDEX_LAST_SEEN_AT in recommendation_indexes:
            op.drop_index(RECOMMENDATIONS_INDEX_LAST_SEEN_AT, table_name=RECOMMENDATIONS_TABLE)
        if RECOMMENDATIONS_INDEX_DECIDED_AT in recommendation_indexes:
            op.drop_index(RECOMMENDATIONS_INDEX_DECIDED_AT, table_name=RECOMMENDATIONS_TABLE)
        if RECOMMENDATIONS_INDEX_ACCEPTED_FEED_ID in recommendation_indexes:
            op.drop_index(RECOMMENDATIONS_INDEX_ACCEPTED_FEED_ID, table_name=RECOMMENDATIONS_TABLE)
        if RECOMMENDATIONS_INDEX_STATUS in recommendation_indexes:
            op.drop_index(RECOMMENDATIONS_INDEX_STATUS, table_name=RECOMMENDATIONS_TABLE)
        if RECOMMENDATIONS_INDEX_USER_ID in recommendation_indexes:
            op.drop_index(RECOMMENDATIONS_INDEX_USER_ID, table_name=RECOMMENDATIONS_TABLE)
        op.drop_table(RECOMMENDATIONS_TABLE)
