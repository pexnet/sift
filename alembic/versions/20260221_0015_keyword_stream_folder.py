"""add folder assignment to keyword streams

Revision ID: 20260221_0015
Revises: 20260219_0014
Create Date: 2026-02-21 12:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260221_0015"
down_revision: str | None = "20260219_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STREAMS_TABLE = "keyword_streams"
FOLDERS_TABLE = "feed_folders"
FOLDER_COLUMN = "folder_id"
STREAM_FOLDER_INDEX = "ix_keyword_streams_folder_id"
STREAM_FOLDER_FK = "fk_keyword_streams_folder_id_feed_folders"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    stream_columns = {column["name"] for column in inspector.get_columns(STREAMS_TABLE)}

    with op.batch_alter_table(STREAMS_TABLE, schema=None) as batch_op:
        if FOLDER_COLUMN not in stream_columns:
            batch_op.add_column(sa.Column(FOLDER_COLUMN, sa.UUID(), nullable=True))

    inspector = sa.inspect(bind)
    stream_indexes = {index["name"] for index in inspector.get_indexes(STREAMS_TABLE)}
    if STREAM_FOLDER_INDEX not in stream_indexes:
        op.create_index(STREAM_FOLDER_INDEX, STREAMS_TABLE, [FOLDER_COLUMN], unique=False)

    inspector = sa.inspect(bind)
    stream_foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys(STREAMS_TABLE)}
    if STREAM_FOLDER_FK not in stream_foreign_keys:
        with op.batch_alter_table(STREAMS_TABLE, schema=None) as batch_op:
            batch_op.create_foreign_key(
                STREAM_FOLDER_FK,
                FOLDERS_TABLE,
                [FOLDER_COLUMN],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    stream_foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys(STREAMS_TABLE)}
    stream_indexes = {index["name"] for index in inspector.get_indexes(STREAMS_TABLE)}
    stream_columns = {column["name"] for column in inspector.get_columns(STREAMS_TABLE)}

    with op.batch_alter_table(STREAMS_TABLE, schema=None) as batch_op:
        if STREAM_FOLDER_FK in stream_foreign_keys:
            batch_op.drop_constraint(STREAM_FOLDER_FK, type_="foreignkey")
        if STREAM_FOLDER_INDEX in stream_indexes:
            batch_op.drop_index(STREAM_FOLDER_INDEX)
        if FOLDER_COLUMN in stream_columns:
            batch_op.drop_column(FOLDER_COLUMN)
