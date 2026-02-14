"""add stream classifier fields

Revision ID: 20260214_0005
Revises: 20260214_0004
Create Date: 2026-02-14 23:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260214_0005"
down_revision: str | None = "20260214_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("keyword_streams", schema=None) as batch_op:
        batch_op.add_column(sa.Column("classifier_mode", sa.String(length=32), nullable=False, server_default="rules_only"))
        batch_op.add_column(sa.Column("classifier_plugin", sa.String(length=128), nullable=True))
        batch_op.add_column(
            sa.Column("classifier_min_confidence", sa.Float(), nullable=False, server_default=sa.text("0.7"))
        )
        batch_op.create_index(batch_op.f("ix_keyword_streams_classifier_mode"), ["classifier_mode"], unique=False)
        batch_op.create_index(batch_op.f("ix_keyword_streams_classifier_plugin"), ["classifier_plugin"], unique=False)

    with op.batch_alter_table("keyword_streams", schema=None) as batch_op:
        batch_op.alter_column("classifier_mode", server_default=None)
        batch_op.alter_column("classifier_min_confidence", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("keyword_streams", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_keyword_streams_classifier_plugin"))
        batch_op.drop_index(batch_op.f("ix_keyword_streams_classifier_mode"))
        batch_op.drop_column("classifier_min_confidence")
        batch_op.drop_column("classifier_plugin")
        batch_op.drop_column("classifier_mode")

