"""add match_query to keyword_streams

Revision ID: 20260216_0008
Revises: 20260214_0007
Create Date: 2026-02-16 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260216_0008"
down_revision: str | None = "20260214_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("keyword_streams", sa.Column("match_query", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("keyword_streams", "match_query")

