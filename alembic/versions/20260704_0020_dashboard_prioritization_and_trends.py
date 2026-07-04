"""add dashboard prioritization and trends tables

Revision ID: 20260704_0020
Revises: 20260301_0019
Create Date: 2026-07-04 16:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260704_0020"
down_revision: str | None = "20260301_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROFILE_TABLE = "user_prioritization_profiles"
PROFILE_UNIQUE_USER = "uq_user_prioritization_profiles_user"
PROFILE_INDEX_USER_ID = "ix_user_prioritization_profiles_user_id"

SNAPSHOTS_TABLE = "trend_snapshots"
SNAPSHOTS_INDEX_USER_ID = "ix_trend_snapshots_user_id"
SNAPSHOTS_INDEX_SCOPE_TYPE = "ix_trend_snapshots_scope_type"
SNAPSHOTS_INDEX_SCOPE_ID = "ix_trend_snapshots_scope_id"
SNAPSHOTS_INDEX_STATUS = "ix_trend_snapshots_status"
SNAPSHOTS_INDEX_USER_SCOPE_CREATED = "ix_trend_snapshots_user_scope_created"

TOPICS_TABLE = "trend_topics"
TOPICS_INDEX_SNAPSHOT_ID = "ix_trend_topics_snapshot_id"
TOPICS_INDEX_TOPIC = "ix_trend_topics_topic"
TOPICS_INDEX_SNAPSHOT_SCORE = "ix_trend_topics_snapshot_score"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if PROFILE_TABLE not in table_names:
        op.create_table(
            PROFILE_TABLE,
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column(
                "source_weights_json",
                sa.Text(),
                nullable=False,
                server_default='{"feed": 40, "monitoring_stream": 60}',
            ),
            sa.Column("recency_horizon_hours", sa.Integer(), nullable=False, server_default="24"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name=PROFILE_UNIQUE_USER),
        )
        op.create_index(PROFILE_INDEX_USER_ID, PROFILE_TABLE, ["user_id"], unique=False)

    table_names = set(inspector.get_table_names())
    if SNAPSHOTS_TABLE not in table_names:
        op.create_table(
            SNAPSHOTS_TABLE,
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("scope_type", sa.String(length=32), nullable=False, server_default="system"),
            sa.Column("scope_id", sa.UUID(), nullable=True),
            sa.Column("short_window_hours", sa.Integer(), nullable=False, server_default="24"),
            sa.Column("baseline_days", sa.Integer(), nullable=False, server_default="14"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(SNAPSHOTS_INDEX_USER_ID, SNAPSHOTS_TABLE, ["user_id"], unique=False)
        op.create_index(SNAPSHOTS_INDEX_SCOPE_TYPE, SNAPSHOTS_TABLE, ["scope_type"], unique=False)
        op.create_index(SNAPSHOTS_INDEX_SCOPE_ID, SNAPSHOTS_TABLE, ["scope_id"], unique=False)
        op.create_index(SNAPSHOTS_INDEX_STATUS, SNAPSHOTS_TABLE, ["status"], unique=False)
        op.create_index(
            SNAPSHOTS_INDEX_USER_SCOPE_CREATED,
            SNAPSHOTS_TABLE,
            ["user_id", "scope_type", "created_at"],
            unique=False,
        )

    table_names = set(inspector.get_table_names())
    if TOPICS_TABLE not in table_names:
        op.create_table(
            TOPICS_TABLE,
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("snapshot_id", sa.UUID(), nullable=False),
            sa.Column("topic", sa.String(length=255), nullable=False),
            sa.Column("momentum_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("short_window_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("baseline_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_diversity_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("representative_article_ids_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["snapshot_id"], ["trend_snapshots.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(TOPICS_INDEX_SNAPSHOT_ID, TOPICS_TABLE, ["snapshot_id"], unique=False)
        op.create_index(TOPICS_INDEX_TOPIC, TOPICS_TABLE, ["topic"], unique=False)
        op.create_index(
            TOPICS_INDEX_SNAPSHOT_SCORE,
            TOPICS_TABLE,
            ["snapshot_id", "momentum_score"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if TOPICS_TABLE in table_names:
        topic_indexes = {index["name"] for index in inspector.get_indexes(TOPICS_TABLE)}
        if TOPICS_INDEX_SNAPSHOT_SCORE in topic_indexes:
            op.drop_index(TOPICS_INDEX_SNAPSHOT_SCORE, table_name=TOPICS_TABLE)
        if TOPICS_INDEX_TOPIC in topic_indexes:
            op.drop_index(TOPICS_INDEX_TOPIC, table_name=TOPICS_TABLE)
        if TOPICS_INDEX_SNAPSHOT_ID in topic_indexes:
            op.drop_index(TOPICS_INDEX_SNAPSHOT_ID, table_name=TOPICS_TABLE)
        op.drop_table(TOPICS_TABLE)

    table_names = set(inspector.get_table_names())
    if SNAPSHOTS_TABLE in table_names:
        snapshot_indexes = {index["name"] for index in inspector.get_indexes(SNAPSHOTS_TABLE)}
        if SNAPSHOTS_INDEX_USER_SCOPE_CREATED in snapshot_indexes:
            op.drop_index(SNAPSHOTS_INDEX_USER_SCOPE_CREATED, table_name=SNAPSHOTS_TABLE)
        if SNAPSHOTS_INDEX_STATUS in snapshot_indexes:
            op.drop_index(SNAPSHOTS_INDEX_STATUS, table_name=SNAPSHOTS_TABLE)
        if SNAPSHOTS_INDEX_SCOPE_ID in snapshot_indexes:
            op.drop_index(SNAPSHOTS_INDEX_SCOPE_ID, table_name=SNAPSHOTS_TABLE)
        if SNAPSHOTS_INDEX_SCOPE_TYPE in snapshot_indexes:
            op.drop_index(SNAPSHOTS_INDEX_SCOPE_TYPE, table_name=SNAPSHOTS_TABLE)
        if SNAPSHOTS_INDEX_USER_ID in snapshot_indexes:
            op.drop_index(SNAPSHOTS_INDEX_USER_ID, table_name=SNAPSHOTS_TABLE)
        op.drop_table(SNAPSHOTS_TABLE)

    table_names = set(inspector.get_table_names())
    if PROFILE_TABLE in table_names:
        profile_indexes = {index["name"] for index in inspector.get_indexes(PROFILE_TABLE)}
        if PROFILE_INDEX_USER_ID in profile_indexes:
            op.drop_index(PROFILE_INDEX_USER_ID, table_name=PROFILE_TABLE)
        op.drop_table(PROFILE_TABLE)
