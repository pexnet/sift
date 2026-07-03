import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import ApiTokenCreate, ApiTokenCreatedOut, ApiTokenOut, ApiTokenRevokeOut
from sift.services.token_service import TokenNotFoundError, token_service

router = APIRouter()


@router.post("", response_model=ApiTokenCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_token(
    payload: ApiTokenCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiTokenCreatedOut:
    raw_token, record = await token_service.create_token(
        session=session,
        user_id=current_user.id,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )
    return ApiTokenCreatedOut(
        id=record.id,
        name=record.name,
        scopes=json.loads(record.scopes_json),
        expires_at=record.expires_at,
        last_used_at=record.last_used_at,
        created_at=record.created_at,
        raw_token=raw_token,
    )


@router.get("", response_model=list[ApiTokenOut])
async def list_tokens(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ApiTokenOut]:
    tokens = await token_service.list_tokens(session=session, user_id=current_user.id)
    result: list[ApiTokenOut] = []
    for t in tokens:
        result.append(
            ApiTokenOut(
                id=t.id,
                name=t.name,
                scopes=json.loads(t.scopes_json) if t.scopes_json else [],
                expires_at=t.expires_at,
                last_used_at=t.last_used_at,
                created_at=t.created_at,
            )
        )
    return result


@router.delete("/{token_id}", response_model=ApiTokenRevokeOut)
async def revoke_token(
    token_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiTokenRevokeOut:
    try:
        await token_service.revoke_token(
            session=session,
            user_id=current_user.id,
            token_id=token_id,
        )
    except TokenNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ApiTokenRevokeOut(revoked=True)
