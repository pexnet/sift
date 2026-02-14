import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import IngestRule
from sift.domain.schemas import IngestRuleCreate, IngestRuleOut, IngestRuleUpdate


class RuleConflictError(Exception):
    pass


class RuleValidationError(Exception):
    pass


class RuleNotFoundError(Exception):
    pass


@dataclass(slots=True)
class CompiledIngestRule:
    id: UUID
    name: str
    priority: int
    include_keywords: list[str]
    exclude_keywords: list[str]
    source_contains: str | None
    language_equals: str | None
    action: str


def _normalize_keywords(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for keyword in keywords:
        item = keyword.strip().lower()
        if item and item not in seen:
            normalized.append(item)
            seen.add(item)
    return normalized


def _keywords_to_json(keywords: list[str]) -> str:
    return json.dumps(_normalize_keywords(keywords))


def _keywords_from_json(raw: str) -> list[str]:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return _normalize_keywords([str(item) for item in loaded])


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_optional_lower(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized else None


def _validate_criteria(
    include_keywords: list[str],
    source_contains: str | None,
    language_equals: str | None,
) -> None:
    if include_keywords:
        return
    if source_contains:
        return
    if language_equals:
        return
    raise RuleValidationError("A rule needs at least one positive criterion (include keyword, source, or language)")


def compile_rule(rule: IngestRule) -> CompiledIngestRule:
    return CompiledIngestRule(
        id=rule.id,
        name=rule.name,
        priority=rule.priority,
        include_keywords=_keywords_from_json(rule.include_keywords_json),
        exclude_keywords=_keywords_from_json(rule.exclude_keywords_json),
        source_contains=_normalize_optional_lower(rule.source_contains),
        language_equals=_normalize_optional_lower(rule.language_equals),
        action=rule.action,
    )


def rule_matches(
    rule: CompiledIngestRule,
    *,
    title: str,
    content_text: str,
    source_url: str | None,
    language: str | None,
) -> bool:
    payload = f"{title}\n{content_text}".lower()
    source = (source_url or "").lower()
    normalized_language = (language or "").lower()

    if rule.include_keywords and not any(keyword in payload for keyword in rule.include_keywords):
        return False
    if rule.exclude_keywords and any(keyword in payload for keyword in rule.exclude_keywords):
        return False
    if rule.source_contains and rule.source_contains not in source:
        return False
    if rule.language_equals and rule.language_equals != normalized_language:
        return False

    return True


class RuleService:
    async def list_rules(self, session: AsyncSession, user_id: UUID) -> list[IngestRule]:
        query = select(IngestRule).where(IngestRule.user_id == user_id).order_by(IngestRule.priority.asc(), IngestRule.name.asc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def list_active_compiled_rules(self, session: AsyncSession, user_id: UUID) -> list[CompiledIngestRule]:
        query = (
            select(IngestRule)
            .where(IngestRule.user_id == user_id, IngestRule.is_active.is_(True))
            .order_by(IngestRule.priority.asc(), IngestRule.name.asc())
        )
        result = await session.execute(query)
        return [compile_rule(rule) for rule in result.scalars().all()]

    async def create_rule(self, session: AsyncSession, user_id: UUID, payload: IngestRuleCreate) -> IngestRule:
        include_keywords = _normalize_keywords(payload.include_keywords)
        exclude_keywords = _normalize_keywords(payload.exclude_keywords)
        source_contains = _normalize_optional_text(payload.source_contains)
        language_equals = _normalize_optional_lower(payload.language_equals)

        _validate_criteria(include_keywords, source_contains, language_equals)

        rule = IngestRule(
            user_id=user_id,
            name=payload.name.strip(),
            is_active=payload.is_active,
            priority=payload.priority,
            include_keywords_json=_keywords_to_json(include_keywords),
            exclude_keywords_json=_keywords_to_json(exclude_keywords),
            source_contains=source_contains,
            language_equals=language_equals,
            action=payload.action,
        )
        session.add(rule)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise RuleConflictError("Rule with the same name already exists") from exc

        await session.refresh(rule)
        return rule

    async def update_rule(
        self,
        session: AsyncSession,
        user_id: UUID,
        rule_id: UUID,
        payload: IngestRuleUpdate,
    ) -> IngestRule:
        rule = await self.get_rule(session=session, user_id=user_id, rule_id=rule_id)
        if rule is None:
            raise RuleNotFoundError(f"Rule {rule_id} not found")

        if payload.name is not None:
            rule.name = payload.name.strip()
        if payload.is_active is not None:
            rule.is_active = payload.is_active
        if payload.priority is not None:
            rule.priority = payload.priority
        if payload.include_keywords is not None:
            rule.include_keywords_json = _keywords_to_json(payload.include_keywords)
        if payload.exclude_keywords is not None:
            rule.exclude_keywords_json = _keywords_to_json(payload.exclude_keywords)
        if payload.source_contains is not None:
            rule.source_contains = _normalize_optional_text(payload.source_contains)
        if payload.language_equals is not None:
            rule.language_equals = _normalize_optional_lower(payload.language_equals)
        if payload.action is not None:
            rule.action = payload.action

        include_keywords = _keywords_from_json(rule.include_keywords_json)
        source_contains = _normalize_optional_text(rule.source_contains)
        language_equals = _normalize_optional_lower(rule.language_equals)
        _validate_criteria(include_keywords, source_contains, language_equals)

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise RuleConflictError("Rule with the same name already exists") from exc

        await session.refresh(rule)
        return rule

    async def delete_rule(self, session: AsyncSession, user_id: UUID, rule_id: UUID) -> None:
        rule = await self.get_rule(session=session, user_id=user_id, rule_id=rule_id)
        if rule is None:
            raise RuleNotFoundError(f"Rule {rule_id} not found")

        await session.delete(rule)
        await session.commit()

    async def get_rule(self, session: AsyncSession, user_id: UUID, rule_id: UUID) -> IngestRule | None:
        query = select(IngestRule).where(IngestRule.id == rule_id, IngestRule.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    def to_out(self, rule: IngestRule) -> IngestRuleOut:
        return IngestRuleOut(
            id=rule.id,
            user_id=rule.user_id,
            name=rule.name,
            is_active=rule.is_active,
            priority=rule.priority,
            include_keywords=_keywords_from_json(rule.include_keywords_json),
            exclude_keywords=_keywords_from_json(rule.exclude_keywords_json),
            source_contains=rule.source_contains,
            language_equals=rule.language_equals,
            action="drop",
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )

    def should_drop_article(
        self,
        rules: list[CompiledIngestRule],
        *,
        title: str,
        content_text: str,
        source_url: str | None,
        language: str | None,
    ) -> bool:
        for rule in rules:
            if rule.action != "drop":
                continue
            if rule_matches(
                rule,
                title=title,
                content_text=content_text,
                source_url=source_url,
                language=language,
            ):
                return True
        return False


rule_service = RuleService()
