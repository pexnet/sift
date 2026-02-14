"""add auth and account models

Revision ID: 20260214_0002
Revises: 20260214_0001
Create Date: 2026-02-14 20:35:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260214_0002"
down_revision: str | None = "20260214_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_is_active"), "users", ["is_active"], unique=False)
    op.create_index(op.f("ix_users_is_admin"), "users", ["is_admin"], unique=False)

    op.create_table(
        "auth_identities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_user_id", sa.String(length=320), nullable=False),
        sa.Column("provider_email", sa.String(length=320), nullable=True),
        sa.Column("password_hash", sa.String(length=1024), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_auth_identity_provider_subject"),
        sa.UniqueConstraint("user_id", "provider", name="uq_auth_identity_user_provider"),
    )
    op.create_index(op.f("ix_auth_identities_provider"), "auth_identities", ["provider"], unique=False)
    op.create_index(op.f("ix_auth_identities_provider_email"), "auth_identities", ["provider_email"], unique=False)
    op.create_index(op.f("ix_auth_identities_user_id"), "auth_identities", ["user_id"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("session_token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_sessions_expires_at"), "user_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_user_sessions_revoked_at"), "user_sessions", ["revoked_at"], unique=False)
    op.create_index(op.f("ix_user_sessions_session_token_hash"), "user_sessions", ["session_token_hash"], unique=True)
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)

    op.create_table(
        "api_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_tokens_expires_at"), "api_tokens", ["expires_at"], unique=False)
    op.create_index(op.f("ix_api_tokens_last_used_at"), "api_tokens", ["last_used_at"], unique=False)
    op.create_index(op.f("ix_api_tokens_revoked_at"), "api_tokens", ["revoked_at"], unique=False)
    op.create_index(op.f("ix_api_tokens_token_hash"), "api_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_api_tokens_user_id"), "api_tokens", ["user_id"], unique=False)

    with op.batch_alter_table("feeds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key("fk_feeds_owner_id_users", "users", ["owner_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index(batch_op.f("ix_feeds_owner_id"), ["owner_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("feeds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_feeds_owner_id"))
        batch_op.drop_constraint("fk_feeds_owner_id_users", type_="foreignkey")
        batch_op.drop_column("owner_id")

    op.drop_index(op.f("ix_api_tokens_user_id"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_token_hash"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_revoked_at"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_last_used_at"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_expires_at"), table_name="api_tokens")
    op.drop_table("api_tokens")

    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_session_token_hash"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_revoked_at"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_expires_at"), table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index(op.f("ix_auth_identities_user_id"), table_name="auth_identities")
    op.drop_index(op.f("ix_auth_identities_provider_email"), table_name="auth_identities")
    op.drop_index(op.f("ix_auth_identities_provider"), table_name="auth_identities")
    op.drop_table("auth_identities")

    op.drop_index(op.f("ix_users_is_admin"), table_name="users")
    op.drop_index(op.f("ix_users_is_active"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

