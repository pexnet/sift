"""add feed lifecycle and fetch health fields

Revision ID: 20260219_0014
Revises: 20260217_0013
Create Date: 2026-02-19 13:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_0014"
down_revision: str | None = "20260217_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("feeds")}

    with op.batch_alter_table("feeds", schema=None) as batch_op:
        if "is_archived" not in columns:
            batch_op.add_column(sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "archived_at" not in columns:
            batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        if "last_fetch_success_at" not in columns:
            batch_op.add_column(sa.Column("last_fetch_success_at", sa.DateTime(timezone=True), nullable=True))
        if "last_fetch_error_at" not in columns:
            batch_op.add_column(sa.Column("last_fetch_error_at", sa.DateTime(timezone=True), nullable=True))

    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("feeds")}
    if "ix_feeds_is_archived" not in existing_indexes:
        op.create_index("ix_feeds_is_archived", "feeds", ["is_archived"], unique=False)

    with op.batch_alter_table("feeds", schema=None) as batch_op:
        if "is_archived" in {column["name"] for column in inspector.get_columns("feeds")}:
            batch_op.alter_column("is_archived", server_default=None)

    op.execute(
        sa.text(
            """
            UPDATE feeds
            SET last_fetch_success_at = last_fetched_at
            WHERE last_fetched_at IS NOT NULL
              AND (last_fetch_error IS NULL OR TRIM(last_fetch_error) = '')
              AND last_fetch_success_at IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE feeds
            SET last_fetch_error_at = last_fetched_at
            WHERE last_fetched_at IS NOT NULL
              AND last_fetch_error IS NOT NULL
              AND TRIM(last_fetch_error) != ''
              AND last_fetch_error_at IS NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("feeds")}
    if "ix_feeds_is_archived" in existing_indexes:
        op.drop_index("ix_feeds_is_archived", table_name="feeds")

    columns = {column["name"] for column in inspector.get_columns("feeds")}
    with op.batch_alter_table("feeds", schema=None) as batch_op:
        if "last_fetch_error_at" in columns:
            batch_op.drop_column("last_fetch_error_at")
        if "last_fetch_success_at" in columns:
            batch_op.drop_column("last_fetch_success_at")
        if "archived_at" in columns:
            batch_op.drop_column("archived_at")
        if "is_archived" in columns:
            batch_op.drop_column("is_archived")
