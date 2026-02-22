"""add article canonical dedup fields

Revision ID: 20260214_0006
Revises: 20260214_0005
Create Date: 2026-02-14 22:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260214_0006"
down_revision: str | None = "20260214_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("canonical_url_normalized", sa.String(length=2000), nullable=True))
        batch_op.add_column(sa.Column("content_fingerprint", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("dedup_confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")))
        batch_op.create_index(
            batch_op.f("ix_articles_canonical_url_normalized"), ["canonical_url_normalized"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_articles_content_fingerprint"), ["content_fingerprint"], unique=False)

    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.alter_column("dedup_confidence", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_articles_content_fingerprint"))
        batch_op.drop_index(batch_op.f("ix_articles_canonical_url_normalized"))
        batch_op.drop_column("dedup_confidence")
        batch_op.drop_column("content_fingerprint")
        batch_op.drop_column("canonical_url_normalized")
