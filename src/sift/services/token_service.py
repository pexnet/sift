"""API token service for MCP and machine-to-machine authentication.

Tokens use SHA-256 hashed storage with a ``sft_`` prefix.
The raw token is returned only once at creation time.
"""

import hashlib
import json
import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import ApiToken

TOKEN_PREFIX = "sft_"
TOKEN_BYTES = 32


class TokenError(Exception):
    pass


class TokenNotFoundError(TokenError):
    pass


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_raw_token() -> str:
    return TOKEN_PREFIX + secrets.token_hex(TOKEN_BYTES)


class TokenService:
    async def create_token(
        self,
        session: AsyncSession,
        user_id: UUID,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[str, ApiToken]:
        raw = _generate_raw_token()
        token = ApiToken(
            user_id=user_id,
            name=name,
            token_hash=_hash_token(raw),
            scopes_json=json.dumps(scopes or []),
            expires_at=expires_at,
        )
        session.add(token)
        await session.commit()
        await session.refresh(token)
        return raw, token

    async def validate_token(self, session: AsyncSession, raw_token: str) -> ApiToken | None:
        if not raw_token.startswith(TOKEN_PREFIX):
            return None
        token_hash = _hash_token(raw_token)
        stmt = select(ApiToken).where(
            ApiToken.token_hash == token_hash,
            ApiToken.revoked_at.is_(None),
        )
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        if token is None:
            return None
        if token.expires_at is not None and token.expires_at < datetime.now(UTC):
            return None
        await session.execute(update(ApiToken).where(ApiToken.id == token.id).values(last_used_at=datetime.now(UTC)))
        await session.commit()
        return token

    async def list_tokens(self, session: AsyncSession, user_id: UUID) -> list[ApiToken]:
        stmt = (
            select(ApiToken)
            .where(
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
            )
            .order_by(ApiToken.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_token(self, session: AsyncSession, user_id: UUID, token_id: UUID) -> None:
        stmt = select(ApiToken).where(
            ApiToken.id == token_id,
            ApiToken.user_id == user_id,
            ApiToken.revoked_at.is_(None),
        )
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        if token is None:
            raise TokenNotFoundError("Token not found or already revoked")
        token.revoked_at = datetime.now(UTC)
        await session.commit()


token_service = TokenService()
