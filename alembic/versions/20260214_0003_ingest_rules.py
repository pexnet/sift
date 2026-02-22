"""add ingest rules

Revision ID: 20260214_0003
Revises: 20260214_0002
Create Date: 2026-02-14 22:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260214_0003"
down_revision: str | None = "20260214_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingest_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("include_keywords_json", sa.Text(), nullable=False),
        sa.Column("exclude_keywords_json", sa.Text(), nullable=False),
        sa.Column("source_contains", sa.String(length=1000), nullable=True),
        sa.Column("language_equals", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_ingest_rules_user_name"),
    )
    op.create_index(op.f("ix_ingest_rules_action"), "ingest_rules", ["action"], unique=False)
    op.create_index(op.f("ix_ingest_rules_is_active"), "ingest_rules", ["is_active"], unique=False)
    op.create_index(op.f("ix_ingest_rules_language_equals"), "ingest_rules", ["language_equals"], unique=False)
    op.create_index(op.f("ix_ingest_rules_priority"), "ingest_rules", ["priority"], unique=False)
    op.create_index(op.f("ix_ingest_rules_user_id"), "ingest_rules", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ingest_rules_user_id"), table_name="ingest_rules")
    op.drop_index(op.f("ix_ingest_rules_priority"), table_name="ingest_rules")
    op.drop_index(op.f("ix_ingest_rules_language_equals"), table_name="ingest_rules")
    op.drop_index(op.f("ix_ingest_rules_is_active"), table_name="ingest_rules")
    op.drop_index(op.f("ix_ingest_rules_action"), table_name="ingest_rules")
    op.drop_table("ingest_rules")
