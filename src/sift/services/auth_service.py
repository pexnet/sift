import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.config import get_settings
from sift.db.models import AuthIdentity, User, UserSession

LOCAL_PROVIDER = "local"
_password_hasher = PasswordHasher()


class AuthError(Exception):
    pass


class AuthenticationError(AuthError):
    pass


class ConflictError(AuthError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


class AuthService:
    async def register_local_user(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        display_name: str = "",
    ) -> User:
        normalized_email = normalize_email(email)

        existing_user_query = select(User).where(User.email == normalized_email)
        existing_user_result = await session.execute(existing_user_query)
        if existing_user_result.scalar_one_or_none() is not None:
            raise ConflictError("An account with this email already exists")

        user = User(email=normalized_email, display_name=display_name.strip())
        session.add(user)
        await session.flush()

        identity = AuthIdentity(
            user_id=user.id,
            provider=LOCAL_PROVIDER,
            provider_user_id=normalized_email,
            provider_email=normalized_email,
            password_hash=hash_password(password),
        )
        session.add(identity)
        await session.commit()
        await session.refresh(user)
        return user

    async def authenticate_local(self, session: AsyncSession, email: str, password: str) -> User:
        normalized_email = normalize_email(email)
        query = (
            select(User, AuthIdentity)
            .join(AuthIdentity, AuthIdentity.user_id == User.id)
            .where(
                User.email == normalized_email,
                AuthIdentity.provider == LOCAL_PROVIDER,
            )
        )
        result = await session.execute(query)
        row = result.one_or_none()
        if row is None:
            raise AuthenticationError("Invalid credentials")

        user, identity = row
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        if not identity.password_hash or not verify_password(password, identity.password_hash):
            raise AuthenticationError("Invalid credentials")
        return user

    async def create_session(
        self,
        session: AsyncSession,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
    ) -> str:
        settings = get_settings()
        raw_token = secrets.token_urlsafe(48)
        token_hash = hash_session_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(days=settings.auth_session_ttl_days)

        user_session = UserSession(
            user_id=user.id,
            session_token_hash=token_hash,
            expires_at=expires_at,
            last_seen_at=datetime.now(UTC),
            ip_address=(ip_address or "")[:64] or None,
            user_agent=(user_agent or "")[:512] or None,
        )
        session.add(user_session)
        await session.commit()
        return raw_token

    async def get_user_by_session_token(self, session: AsyncSession, raw_token: str) -> User | None:
        token_hash = hash_session_token(raw_token)
        now = datetime.now(UTC)

        query = (
            select(User, UserSession)
            .join(UserSession, UserSession.user_id == User.id)
            .where(
                UserSession.session_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
                User.is_active.is_(True),
            )
        )
        try:
            result = await session.execute(query)
        except SQLAlchemyError:
            await session.rollback()
            return None
        row = result.one_or_none()
        if row is None:
            return None

        user, user_session = row
        user_session.last_seen_at = now
        try:
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
        return user

    async def revoke_session(self, session: AsyncSession, raw_token: str) -> None:
        token_hash = hash_session_token(raw_token)
        query = select(UserSession).where(
            UserSession.session_token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
        result = await session.execute(query)
        user_session = result.scalar_one_or_none()
        if user_session is None:
            return

        user_session.revoked_at = datetime.now(UTC)
        await session.commit()


auth_service = AuthService()
