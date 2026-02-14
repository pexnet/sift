from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import IngestRuleCreate, IngestRuleOut, IngestRuleUpdate
from sift.services.rule_service import RuleConflictError, RuleNotFoundError, RuleValidationError, rule_service

router = APIRouter()


@router.get("", response_model=list[IngestRuleOut])
async def list_rules(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[IngestRuleOut]:
    rules = await rule_service.list_rules(session=session, user_id=current_user.id)
    return [rule_service.to_out(rule) for rule in rules]


@router.post("", response_model=IngestRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: IngestRuleCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> IngestRuleOut:
    try:
        rule = await rule_service.create_rule(session=session, user_id=current_user.id, payload=payload)
    except RuleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RuleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return rule_service.to_out(rule)


@router.patch("/{rule_id}", response_model=IngestRuleOut)
async def update_rule(
    rule_id: UUID,
    payload: IngestRuleUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> IngestRuleOut:
    try:
        rule = await rule_service.update_rule(
            session=session,
            user_id=current_user.id,
            rule_id=rule_id,
            payload=payload,
        )
    except RuleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RuleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return rule_service.to_out(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await rule_service.delete_rule(session=session, user_id=current_user.id, rule_id=rule_id)
    except RuleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

