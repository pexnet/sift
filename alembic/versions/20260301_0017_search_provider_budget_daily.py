"""add search provider daily budget ledger

Revision ID: 20260301_0017
Revises: 20260222_0016
Create Date: 2026-03-01 14:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260301_0017"
down_revision: str | None = "20260222_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "search_provider_budget_daily"
UNIQUE_PROVIDER_DAY = "uq_search_provider_budget_daily_provider_day"
INDEX_PROVIDER_ID = "ix_search_provider_budget_daily_provider_id"
INDEX_DAY_UTC = "ix_search_provider_budget_daily_day_utc"
INDEX_LAST_REQUEST_AT = "ix_search_provider_budget_daily_last_request_at"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if TABLE_NAME in table_names:
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("day_utc", sa.Date(), nullable=False),
        sa.Column("requests_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "day_utc", name=UNIQUE_PROVIDER_DAY),
    )
    op.create_index(INDEX_PROVIDER_ID, TABLE_NAME, ["provider_id"], unique=False)
    op.create_index(INDEX_DAY_UTC, TABLE_NAME, ["day_utc"], unique=False)
    op.create_index(INDEX_LAST_REQUEST_AT, TABLE_NAME, ["last_request_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if TABLE_NAME not in table_names:
        return

    indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if INDEX_LAST_REQUEST_AT in indexes:
        op.drop_index(INDEX_LAST_REQUEST_AT, table_name=TABLE_NAME)
    if INDEX_DAY_UTC in indexes:
        op.drop_index(INDEX_DAY_UTC, table_name=TABLE_NAME)
    if INDEX_PROVIDER_ID in indexes:
        op.drop_index(INDEX_PROVIDER_ID, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
