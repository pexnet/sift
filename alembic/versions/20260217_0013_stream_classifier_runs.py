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


def upgrade() -> None:
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
    op.create_index("ix_stream_classifier_runs_user_id", "stream_classifier_runs", ["user_id"], unique=False)
    op.create_index("ix_stream_classifier_runs_stream_id", "stream_classifier_runs", ["stream_id"], unique=False)
    op.create_index("ix_stream_classifier_runs_article_id", "stream_classifier_runs", ["article_id"], unique=False)
    op.create_index("ix_stream_classifier_runs_feed_id", "stream_classifier_runs", ["feed_id"], unique=False)
    op.create_index(
        "ix_stream_classifier_runs_classifier_mode",
        "stream_classifier_runs",
        ["classifier_mode"],
        unique=False,
    )
    op.create_index("ix_stream_classifier_runs_plugin_name", "stream_classifier_runs", ["plugin_name"], unique=False)
    op.create_index("ix_stream_classifier_runs_provider", "stream_classifier_runs", ["provider"], unique=False)
    op.create_index("ix_stream_classifier_runs_model_name", "stream_classifier_runs", ["model_name"], unique=False)
    op.create_index(
        "ix_stream_classifier_runs_model_version",
        "stream_classifier_runs",
        ["model_version"],
        unique=False,
    )
    op.create_index("ix_stream_classifier_runs_matched", "stream_classifier_runs", ["matched"], unique=False)
    op.create_index("ix_stream_classifier_runs_run_status", "stream_classifier_runs", ["run_status"], unique=False)
    op.create_index("ix_stream_classifier_runs_created_at", "stream_classifier_runs", ["created_at"], unique=False)
    op.create_index(
        "ix_stream_classifier_runs_stream_created",
        "stream_classifier_runs",
        ["stream_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_stream_classifier_runs_stream_created", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_created_at", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_run_status", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_matched", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_model_version", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_model_name", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_provider", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_plugin_name", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_classifier_mode", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_feed_id", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_article_id", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_stream_id", table_name="stream_classifier_runs")
    op.drop_index("ix_stream_classifier_runs_user_id", table_name="stream_classifier_runs")
    op.drop_table("stream_classifier_runs")

