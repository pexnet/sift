"""add article fulltext persistence table

Revision ID: 20260222_0016
Revises: 20260221_0015
Create Date: 2026-02-22 19:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260222_0016"
down_revision: str | None = "20260221_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FULLTEXTS_TABLE = "article_fulltexts"
ARTICLE_FK_NAME = "fk_article_fulltexts_article_id_articles"
ARTICLE_UNIQUE_NAME = "uq_article_fulltexts_article"
INDEX_ARTICLE_ID = "ix_article_fulltexts_article_id"
INDEX_STATUS = "ix_article_fulltexts_status"
INDEX_FETCHED_AT = "ix_article_fulltexts_fetched_at"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if FULLTEXTS_TABLE in table_names:
        return

    op.create_table(
        FULLTEXTS_TABLE,
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("final_url", sa.String(length=2000), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("extractor", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], name=ARTICLE_FK_NAME, ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", name=ARTICLE_UNIQUE_NAME),
    )
    op.create_index(INDEX_ARTICLE_ID, FULLTEXTS_TABLE, ["article_id"], unique=False)
    op.create_index(INDEX_STATUS, FULLTEXTS_TABLE, ["status"], unique=False)
    op.create_index(INDEX_FETCHED_AT, FULLTEXTS_TABLE, ["fetched_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if FULLTEXTS_TABLE not in table_names:
        return

    indexes = {index["name"] for index in inspector.get_indexes(FULLTEXTS_TABLE)}
    if INDEX_FETCHED_AT in indexes:
        op.drop_index(INDEX_FETCHED_AT, table_name=FULLTEXTS_TABLE)
    if INDEX_STATUS in indexes:
        op.drop_index(INDEX_STATUS, table_name=FULLTEXTS_TABLE)
    if INDEX_ARTICLE_ID in indexes:
        op.drop_index(INDEX_ARTICLE_ID, table_name=FULLTEXTS_TABLE)
    op.drop_table(FULLTEXTS_TABLE)
