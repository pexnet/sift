"""add discovery streams table

Revision ID: 20260301_0018
Revises: 20260301_0017
Create Date: 2026-03-01 16:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260301_0018"
down_revision: str | None = "20260301_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "discovery_streams"
UNIQUE_USER_NAME = "uq_discovery_streams_user_name"
INDEX_USER_ID = "ix_discovery_streams_user_id"
INDEX_IS_ACTIVE = "ix_discovery_streams_is_active"
INDEX_PRIORITY = "ix_discovery_streams_priority"
INDEX_USER_ACTIVE_PRIORITY = "ix_discovery_streams_user_active_priority"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if TABLE_NAME in table_names:
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("match_query", sa.Text(), nullable=True),
        sa.Column("include_keywords_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("exclude_keywords_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name=UNIQUE_USER_NAME),
    )
    op.create_index(INDEX_USER_ID, TABLE_NAME, ["user_id"], unique=False)
    op.create_index(INDEX_IS_ACTIVE, TABLE_NAME, ["is_active"], unique=False)
    op.create_index(INDEX_PRIORITY, TABLE_NAME, ["priority"], unique=False)
    op.create_index(INDEX_USER_ACTIVE_PRIORITY, TABLE_NAME, ["user_id", "is_active", "priority"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if TABLE_NAME not in table_names:
        return

    indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if INDEX_USER_ACTIVE_PRIORITY in indexes:
        op.drop_index(INDEX_USER_ACTIVE_PRIORITY, table_name=TABLE_NAME)
    if INDEX_PRIORITY in indexes:
        op.drop_index(INDEX_PRIORITY, table_name=TABLE_NAME)
    if INDEX_IS_ACTIVE in indexes:
        op.drop_index(INDEX_IS_ACTIVE, table_name=TABLE_NAME)
    if INDEX_USER_ID in indexes:
        op.drop_index(INDEX_USER_ID, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
