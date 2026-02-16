"""add match_reason to keyword_stream_matches

Revision ID: 20260216_0010
Revises: 20260216_0009
Create Date: 2026-02-16 21:35:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260216_0010"
down_revision: str | None = "20260216_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("keyword_stream_matches", sa.Column("match_reason", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("keyword_stream_matches", "match_reason")
