"""add keyword streams

Revision ID: 20260214_0004
Revises: 20260214_0003
Create Date: 2026-02-14 23:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260214_0004"
down_revision: str | None = "20260214_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "keyword_streams",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("include_keywords_json", sa.Text(), nullable=False),
        sa.Column("exclude_keywords_json", sa.Text(), nullable=False),
        sa.Column("source_contains", sa.String(length=1000), nullable=True),
        sa.Column("language_equals", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_keyword_streams_user_name"),
    )
    op.create_index(op.f("ix_keyword_streams_is_active"), "keyword_streams", ["is_active"], unique=False)
    op.create_index(op.f("ix_keyword_streams_language_equals"), "keyword_streams", ["language_equals"], unique=False)
    op.create_index(op.f("ix_keyword_streams_priority"), "keyword_streams", ["priority"], unique=False)
    op.create_index(op.f("ix_keyword_streams_user_id"), "keyword_streams", ["user_id"], unique=False)

    op.create_table(
        "keyword_stream_matches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("stream_id", sa.UUID(), nullable=False),
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stream_id"], ["keyword_streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_id", "article_id", name="uq_keyword_stream_matches_stream_article"),
    )
    op.create_index(
        op.f("ix_keyword_stream_matches_article_id"), "keyword_stream_matches", ["article_id"], unique=False
    )
    op.create_index(
        op.f("ix_keyword_stream_matches_matched_at"), "keyword_stream_matches", ["matched_at"], unique=False
    )
    op.create_index(op.f("ix_keyword_stream_matches_stream_id"), "keyword_stream_matches", ["stream_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_keyword_stream_matches_stream_id"), table_name="keyword_stream_matches")
    op.drop_index(op.f("ix_keyword_stream_matches_matched_at"), table_name="keyword_stream_matches")
    op.drop_index(op.f("ix_keyword_stream_matches_article_id"), table_name="keyword_stream_matches")
    op.drop_table("keyword_stream_matches")

    op.drop_index(op.f("ix_keyword_streams_user_id"), table_name="keyword_streams")
    op.drop_index(op.f("ix_keyword_streams_priority"), table_name="keyword_streams")
    op.drop_index(op.f("ix_keyword_streams_language_equals"), table_name="keyword_streams")
    op.drop_index(op.f("ix_keyword_streams_is_active"), table_name="keyword_streams")
    op.drop_table("keyword_streams")
