"""add feed folders

Revision ID: 20260214_0007
Revises: 20260214_0006
Create Date: 2026-02-14 23:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260214_0007"
down_revision: str | None = "20260214_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feed_folders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_feed_folders_user_name"),
    )
    op.create_index(op.f("ix_feed_folders_user_id"), "feed_folders", ["user_id"], unique=False)
    op.create_index(op.f("ix_feed_folders_sort_order"), "feed_folders", ["sort_order"], unique=False)

    with op.batch_alter_table("feeds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("folder_id", sa.UUID(), nullable=True))
        batch_op.create_index(batch_op.f("ix_feeds_folder_id"), ["folder_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_feeds_folder_id_feed_folders", "feed_folders", ["folder_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("feeds", schema=None) as batch_op:
        batch_op.drop_constraint("fk_feeds_folder_id_feed_folders", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_feeds_folder_id"))
        batch_op.drop_column("folder_id")

    op.drop_index(op.f("ix_feed_folders_sort_order"), table_name="feed_folders")
    op.drop_index(op.f("ix_feed_folders_user_id"), table_name="feed_folders")
    op.drop_table("feed_folders")
