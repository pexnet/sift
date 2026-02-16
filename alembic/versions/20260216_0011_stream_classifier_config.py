"""add classifier_config_json to keyword_streams

Revision ID: 20260216_0011
Revises: 20260216_0010
Create Date: 2026-02-16 22:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260216_0011"
down_revision: str | None = "20260216_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "keyword_streams",
        sa.Column("classifier_config_json", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("keyword_streams", "classifier_config_json")
