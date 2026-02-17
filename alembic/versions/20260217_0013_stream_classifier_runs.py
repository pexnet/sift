"""add stream_classifier_runs table for classifier run persistence

Revision ID: 20260217_0013
Revises: 20260216_0012
Create Date: 2026-02-17 21:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260217_0013"
down_revision: str | None = "20260216_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INDEX_DEFS: list[tuple[str, list[str]]] = [
    ("ix_stream_classifier_runs_user_id", ["user_id"]),
    ("ix_stream_classifier_runs_stream_id", ["stream_id"]),
    ("ix_stream_classifier_runs_article_id", ["article_id"]),
    ("ix_stream_classifier_runs_feed_id", ["feed_id"]),
    ("ix_stream_classifier_runs_classifier_mode", ["classifier_mode"]),
    ("ix_stream_classifier_runs_plugin_name", ["plugin_name"]),
    ("ix_stream_classifier_runs_provider", ["provider"]),
    ("ix_stream_classifier_runs_model_name", ["model_name"]),
    ("ix_stream_classifier_runs_model_version", ["model_version"]),
    ("ix_stream_classifier_runs_matched", ["matched"]),
    ("ix_stream_classifier_runs_run_status", ["run_status"]),
    ("ix_stream_classifier_runs_created_at", ["created_at"]),
    ("ix_stream_classifier_runs_stream_created", ["stream_id", "created_at"]),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("stream_classifier_runs"):
        op.create_table(
            "stream_classifier_runs",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("stream_id", sa.UUID(), nullable=False),
            sa.Column("article_id", sa.UUID(), nullable=False),
            sa.Column("feed_id", sa.UUID(), nullable=True),
            sa.Column("classifier_mode", sa.String(length=32), nullable=False),
            sa.Column("plugin_name", sa.String(length=128), nullable=False),
            sa.Column("provider", sa.String(length=128), nullable=True),
            sa.Column("model_name", sa.String(length=255), nullable=True),
            sa.Column("model_version", sa.String(length=128), nullable=True),
            sa.Column("matched", sa.Boolean(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("threshold", sa.Float(), nullable=False),
            sa.Column("reason", sa.String(length=1000), nullable=True),
            sa.Column("run_status", sa.String(length=32), nullable=False),
            sa.Column("error_message", sa.String(length=1000), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["feed_id"], ["feeds.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["stream_id"], ["keyword_streams.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    existing_indexes = {index["name"] for index in inspector.get_indexes("stream_classifier_runs")}
    for index_name, columns in INDEX_DEFS:
        if index_name in existing_indexes:
            continue
        op.create_index(index_name, "stream_classifier_runs", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("stream_classifier_runs"):
        return
    existing_indexes = {index["name"] for index in inspector.get_indexes("stream_classifier_runs")}
    for index_name, _ in reversed(INDEX_DEFS):
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="stream_classifier_runs")
    op.drop_table("stream_classifier_runs")
