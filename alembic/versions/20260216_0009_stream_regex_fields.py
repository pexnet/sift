"""add regex matcher fields to keyword_streams

Revision ID: 20260216_0009
Revises: 20260216_0008
Create Date: 2026-02-16 21:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260216_0009"
down_revision: str | None = "20260216_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "keyword_streams",
        sa.Column("include_regex_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "keyword_streams",
        sa.Column("exclude_regex_json", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("keyword_streams", "exclude_regex_json")
    op.drop_column("keyword_streams", "include_regex_json")
