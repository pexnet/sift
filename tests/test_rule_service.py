from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import User
from sift.domain.schemas import IngestRuleCreate, IngestRuleUpdate
from sift.services.rule_service import (
    CompiledIngestRule,
    RuleConflictError,
    RuleValidationError,
    rule_matches,
    rule_service,
)


@pytest.mark.asyncio
async def test_create_rule_requires_positive_criteria() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="rules@example.com")
        session.add(user)
        await session.commit()

        with pytest.raises(RuleValidationError):
            await rule_service.create_rule(
                session=session,
                user_id=user.id,
                payload=IngestRuleCreate(name="bad-empty", include_keywords=[], source_contains=None, language_equals=None),
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_update_rule_roundtrip() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="rules2@example.com")
        session.add(user)
        await session.commit()

        created = await rule_service.create_rule(
            session=session,
            user_id=user.id,
            payload=IngestRuleCreate(
                name="drop-tracking",
                include_keywords=["tracking", "ads"],
                exclude_keywords=["not ad"],
                source_contains="example.com",
            ),
        )
        assert created.name == "drop-tracking"

        updated = await rule_service.update_rule(
            session=session,
            user_id=user.id,
            rule_id=created.id,
            payload=IngestRuleUpdate(priority=10, language_equals="en"),
        )
        assert updated.priority == 10
        assert updated.language_equals == "en"

        rules = await rule_service.list_active_compiled_rules(session=session, user_id=user.id)
        assert len(rules) == 1
        assert rules[0].priority == 10

    await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_rule_name_conflict() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="rules3@example.com")
        session.add(user)
        await session.commit()

        payload = IngestRuleCreate(name="dup", include_keywords=["ai"])
        await rule_service.create_rule(session=session, user_id=user.id, payload=payload)
        with pytest.raises(RuleConflictError):
            await rule_service.create_rule(session=session, user_id=user.id, payload=payload)

    await engine.dispose()


def test_rule_matches_include_exclude_source_language() -> None:
    rule = CompiledIngestRule(
        id=uuid4(),
        name="example",
        priority=100,
        include_keywords=["ai", "llm"],
        exclude_keywords=["sports"],
        source_contains="tech.example.com",
        language_equals="en",
        action="drop",
    )

    assert (
        rule_matches(
            rule,
            title="AI launch",
            content_text="New llm update",
            source_url="https://tech.example.com/rss",
            language="en",
        )
        is True
    )

    assert (
        rule_matches(
            rule,
            title="Sports AI",
            content_text="sports result",
            source_url="https://tech.example.com/rss",
            language="en",
        )
        is False
    )

