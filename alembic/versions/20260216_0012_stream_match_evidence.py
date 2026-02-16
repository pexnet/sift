"""add match_evidence_json to keyword_stream_matches

Revision ID: 20260216_0012
Revises: 20260216_0011
Create Date: 2026-02-16 23:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260216_0012"
down_revision: str | None = "20260216_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("keyword_stream_matches", sa.Column("match_evidence_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("keyword_stream_matches", "match_evidence_json")
