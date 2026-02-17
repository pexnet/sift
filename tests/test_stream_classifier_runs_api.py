from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.db.base import Base
from sift.db.models import Article, Feed, KeywordStream, StreamClassifierRun, User
from sift.db.session import get_db_session
from sift.main import app


def test_stream_classifier_runs_api_lists_runs_for_stream() -> None:
    db_path = Path("test_stream_classifier_runs_api.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> tuple[User, UUID]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_maker() as session:
            user = User(email="api-stream-classifier-runs@example.com")
            session.add(user)
            await session.flush()

            feed = Feed(owner_id=user.id, title="Owned Feed", url="https://api-stream-classifier-runs.example.com/rss")
            session.add(feed)
            await session.flush()

            article = Article(
                feed_id=feed.id,
                source_id="a1",
                title="Microsoft Sentinel alert",
                content_text="security monitoring",
            )
            session.add(article)
            await session.flush()

            stream = KeywordStream(
                user_id=user.id,
                name="security",
                include_keywords_json='["microsoft"]',
                exclude_keywords_json="[]",
                include_regex_json="[]",
                exclude_regex_json="[]",
                classifier_mode="classifier_only",
                classifier_plugin="keyword_heuristic_classifier",
                classifier_config_json="{}",
                classifier_min_confidence=0.7,
            )
            session.add(stream)
            await session.flush()

            classifier_run = StreamClassifierRun(
                user_id=user.id,
                stream_id=stream.id,
                article_id=article.id,
                feed_id=feed.id,
                classifier_mode="classifier_only",
                plugin_name="keyword_heuristic_classifier",
                provider="builtin",
                model_name="keyword_heuristic",
                model_version="v1",
                matched=True,
                confidence=0.9,
                threshold=0.7,
                reason="test reason",
                run_status="ok",
                error_message=None,
                duration_ms=12,
            )
            session.add(classifier_run)
            await session.commit()
            return user, stream.id

    import asyncio

    user, stream_id = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/streams/{stream_id}/classifier-runs")
            assert response.status_code == 200
            payload = response.json()
            assert len(payload) == 1
            assert payload[0]["stream_id"] == str(stream_id)
            assert payload[0]["plugin_name"] == "keyword_heuristic_classifier"
            assert payload[0]["provider"] == "builtin"
            assert payload[0]["model_name"] == "keyword_heuristic"
            assert payload[0]["model_version"] == "v1"
            assert payload[0]["run_status"] == "ok"
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()

