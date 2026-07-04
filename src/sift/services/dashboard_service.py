import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, ArticleState, Feed, KeywordStream, KeywordStreamMatch, UserPrioritizationProfile
from sift.domain.schemas import (
    DashboardFeedHealthCardOut,
    DashboardFeedHealthQueueLagOut,
    DashboardMonitoringSignalsOut,
    DashboardMonitoringSignalStreamOut,
    DashboardPrioritizedArticleOut,
    DashboardPrioritizedQueueOut,
    DashboardPriorityProfileOut,
    DashboardPriorityProfileUpdate,
    DashboardSavedFollowupItemOut,
    DashboardSavedFollowupOut,
)

DEFAULT_SOURCE_WEIGHTS = {"feed": 40, "monitoring_stream": 60}
DEFAULT_RECENCY_HORIZON_HOURS = 24
ALLOWED_SOURCE_WEIGHT_KEYS = frozenset(DEFAULT_SOURCE_WEIGHTS)


class DashboardValidationError(Exception):
    pass


def _decode_source_weights(raw_value: str | None) -> dict[str, int]:
    if not raw_value:
        return dict(DEFAULT_SOURCE_WEIGHTS)
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise DashboardValidationError("Invalid source weight profile JSON") from exc
    if not isinstance(payload, dict):
        raise DashboardValidationError("Invalid source weight profile JSON")
    return _validate_source_weights(payload)


def _validate_source_weights(source_weights: dict[str, object]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key, value in source_weights.items():
        if key not in ALLOWED_SOURCE_WEIGHT_KEYS:
            raise DashboardValidationError(f"Unsupported source weight key: {key}")
        if not isinstance(value, int):
            raise DashboardValidationError(f"Invalid source weight for {key}: must be an integer")
        if value < 0 or value > 100:
            raise DashboardValidationError(f"Invalid source weight for {key}: must be between 0 and 100")
        normalized[key] = value
    return normalized


def _utc_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _recency_score(*, article_time: datetime | None, horizon_hours: int, now: datetime) -> float:
    if article_time is None:
        return 0.0
    age_hours = max((now - _utc_datetime(article_time)).total_seconds() / 3600, 0.0)
    if horizon_hours <= 0 or age_hours >= horizon_hours:
        return 0.0
    return round((1.0 - (age_hours / horizon_hours)) * 20.0, 4)


def _feed_stale_threshold_seconds(feed: Feed) -> float:
    return float(max(6 * 3600, 4 * feed.fetch_interval_minutes * 60))


def _is_feed_stale(feed: Feed, now: datetime) -> bool:
    if feed.is_archived or not feed.is_active:
        return False
    if feed.last_fetch_success_at is None:
        return True
    age_seconds = max((now - _utc_datetime(feed.last_fetch_success_at)).total_seconds(), 0.0)
    return age_seconds > _feed_stale_threshold_seconds(feed)


class DashboardService:
    async def get_prioritization_profile(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
    ) -> DashboardPriorityProfileOut:
        profile = await self._get_profile_row(session=session, user_id=user_id)
        if profile is None:
            return DashboardPriorityProfileOut(
                source_weights=dict(DEFAULT_SOURCE_WEIGHTS),
                recency_horizon_hours=DEFAULT_RECENCY_HORIZON_HOURS,
            )
        return DashboardPriorityProfileOut(
            source_weights=_decode_source_weights(profile.source_weights_json),
            recency_horizon_hours=profile.recency_horizon_hours,
        )

    async def update_prioritization_profile(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        payload: DashboardPriorityProfileUpdate,
    ) -> DashboardPriorityProfileOut:
        profile = await self._get_profile_row(session=session, user_id=user_id)
        existing_weights = (
            _decode_source_weights(profile.source_weights_json) if profile is not None else dict(DEFAULT_SOURCE_WEIGHTS)
        )
        recency_horizon_hours = profile.recency_horizon_hours if profile is not None else DEFAULT_RECENCY_HORIZON_HOURS

        if payload.source_weights is not None:
            existing_weights.update(_validate_source_weights(dict(payload.source_weights)))
        if payload.recency_horizon_hours is not None:
            recency_horizon_hours = payload.recency_horizon_hours

        if profile is None:
            profile = UserPrioritizationProfile(user_id=user_id)
            session.add(profile)

        profile.source_weights_json = json.dumps(existing_weights, sort_keys=True)
        profile.recency_horizon_hours = recency_horizon_hours
        await session.commit()
        await session.refresh(profile)
        return DashboardPriorityProfileOut(
            source_weights=_decode_source_weights(profile.source_weights_json),
            recency_horizon_hours=profile.recency_horizon_hours,
        )

    async def get_prioritized_queue(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        limit: int = 10,
    ) -> DashboardPrioritizedQueueOut:
        profile = await self.get_prioritization_profile(session=session, user_id=user_id)
        state_user_key = str(user_id)
        is_read_expr = func.coalesce(ArticleState.is_read, False)
        is_starred_expr = func.coalesce(ArticleState.is_starred, False)
        is_archived_expr = func.coalesce(ArticleState.is_archived, False)
        rows_result = await session.execute(
            select(
                Article,
                Feed.title.label("feed_title"),
                is_read_expr.label("is_read"),
                is_starred_expr.label("is_starred"),
                KeywordStream.id.label("stream_id"),
                KeywordStream.name.label("stream_name"),
            )
            .join(Feed, Feed.id == Article.feed_id)
            .outerjoin(
                ArticleState,
                and_(ArticleState.article_id == Article.id, ArticleState.user_id == state_user_key),
            )
            .outerjoin(KeywordStreamMatch, KeywordStreamMatch.article_id == Article.id)
            .outerjoin(
                KeywordStream,
                and_(KeywordStream.id == KeywordStreamMatch.stream_id, KeywordStream.user_id == user_id),
            )
            .where(
                Feed.owner_id == user_id,
                is_read_expr.is_(False),
                is_archived_expr.is_(False),
            )
            .order_by(Article.created_at.desc())
            .limit(max(limit * 4, limit))
        )

        now = datetime.now(UTC)
        by_article_id: dict[UUID, DashboardPrioritizedArticleOut] = {}
        monitoring_streams: dict[UUID, list[str]] = {}
        for row in rows_result.all():
            article: Article = row[0]
            feed_title: str = row[1]
            is_read = bool(row[2])
            is_starred = bool(row[3])
            stream_id: UUID | None = row[4]
            stream_name: str | None = row[5]

            if stream_id is not None and stream_name:
                monitoring_streams.setdefault(article.id, [])
                if stream_name not in monitoring_streams[article.id]:
                    monitoring_streams[article.id].append(stream_name)

            if article.id in by_article_id:
                continue

            recency = _recency_score(
                article_time=article.published_at or article.created_at,
                horizon_hours=profile.recency_horizon_hours,
                now=now,
            )
            base_score = float(profile.source_weights.get("feed", DEFAULT_SOURCE_WEIGHTS["feed"]))
            score_breakdown = {
                "feed_base": base_score,
                "recency": recency,
                "monitoring_signal_bonus": 0.0,
            }
            by_article_id[article.id] = DashboardPrioritizedArticleOut(
                article_id=article.id,
                title=article.title,
                feed_title=feed_title,
                canonical_url=article.canonical_url,
                published_at=article.published_at,
                created_at=article.created_at,
                is_read=is_read,
                is_starred=is_starred,
                priority_score=base_score + recency,
                score_breakdown=score_breakdown,
                why_prioritized=["Unread article from an owned feed"],
            )

        items: list[DashboardPrioritizedArticleOut] = []
        monitoring_weight = float(
            profile.source_weights.get("monitoring_stream", DEFAULT_SOURCE_WEIGHTS["monitoring_stream"])
        )
        for article_id, item in by_article_id.items():
            stream_names = monitoring_streams.get(article_id, [])
            score_breakdown = dict(item.score_breakdown)
            why_prioritized = list(item.why_prioritized)
            if stream_names:
                score_breakdown["monitoring_signal_bonus"] = monitoring_weight
                why_prioritized.append(f"Matched monitoring stream: {', '.join(stream_names)}")
            priority_score = round(sum(score_breakdown.values()), 4)
            items.append(
                item.model_copy(
                    update={
                        "priority_score": priority_score,
                        "score_breakdown": score_breakdown,
                        "why_prioritized": why_prioritized,
                    }
                )
            )

        items.sort(
            key=lambda item: (item.priority_score, _utc_datetime(item.published_at or item.created_at)), reverse=True
        )
        return DashboardPrioritizedQueueOut(
            status="ready",
            reason=None,
            dependency_spec=None,
            last_updated_at=now,
            profile=profile,
            items=items[:limit],
        )

    async def get_feed_health_card(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
    ) -> DashboardFeedHealthCardOut:
        now = datetime.now(UTC)
        feeds_result = await session.execute(select(Feed).where(Feed.owner_id == user_id))
        feeds = feeds_result.scalars().all()
        stale_feed_count = sum(1 for feed in feeds if _is_feed_stale(feed, now))
        error_feed_count = sum(1 for feed in feeds if (feed.last_fetch_error or "").strip())
        success_ages = [
            max((now - _utc_datetime(feed.last_fetch_success_at)).total_seconds() / 3600, 0.0)
            for feed in feeds
            if feed.last_fetch_success_at is not None
        ]
        oldest_success_age_hours = round(max(success_ages), 2) if success_ages else None
        return DashboardFeedHealthCardOut(
            status="ready",
            reason=None,
            dependency_spec=None,
            last_updated_at=now,
            stale_feed_count=stale_feed_count,
            error_feed_count=error_feed_count,
            oldest_success_age_hours=oldest_success_age_hours,
            queue_lag=DashboardFeedHealthQueueLagOut(unavailable_reason="Worker queue metrics are not available yet."),
        )

    async def get_saved_followup_card(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        limit: int = 5,
    ) -> DashboardSavedFollowupOut:
        now = datetime.now(UTC)
        state_user_key = str(user_id)
        saved_count_result = await session.execute(
            select(func.count(ArticleState.id))
            .select_from(ArticleState)
            .join(Article, Article.id == ArticleState.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .where(
                Feed.owner_id == user_id,
                ArticleState.user_id == state_user_key,
                ArticleState.is_starred.is_(True),
                func.coalesce(ArticleState.is_archived, False).is_(False),
            )
        )
        saved_count = int(saved_count_result.scalar_one() or 0)
        rows_result = await session.execute(
            select(Article, Feed.title.label("feed_title"), ArticleState.updated_at.label("saved_at"))
            .select_from(ArticleState)
            .join(Article, Article.id == ArticleState.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .where(
                Feed.owner_id == user_id,
                ArticleState.user_id == state_user_key,
                ArticleState.is_starred.is_(True),
                func.coalesce(ArticleState.is_archived, False).is_(False),
            )
            .order_by(ArticleState.updated_at.desc(), Article.created_at.desc())
            .limit(limit)
        )
        latest_items = [
            DashboardSavedFollowupItemOut(
                article_id=article.id,
                title=article.title,
                feed_title=feed_title,
                canonical_url=article.canonical_url,
                published_at=article.published_at,
                saved_at=saved_at,
            )
            for article, feed_title, saved_at in rows_result.all()
        ]
        return DashboardSavedFollowupOut(
            status="ready",
            reason=None,
            dependency_spec=None,
            last_updated_at=now,
            saved_count=saved_count,
            latest_items=latest_items,
        )

    async def get_monitoring_signals_card(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        window_hours: int = 24,
    ) -> DashboardMonitoringSignalsOut:
        now = datetime.now(UTC)
        threshold = now - timedelta(hours=window_hours)
        streams_result = await session.execute(
            select(KeywordStream)
            .where(KeywordStream.user_id == user_id, KeywordStream.is_active.is_(True))
            .order_by(KeywordStream.priority.asc(), KeywordStream.created_at.asc())
        )
        streams = streams_result.scalars().all()
        stream_items: list[DashboardMonitoringSignalStreamOut] = []
        for stream in streams:
            rows_result = await session.execute(
                select(KeywordStreamMatch, ArticleState.is_read)
                .select_from(KeywordStreamMatch)
                .join(Article, Article.id == KeywordStreamMatch.article_id)
                .join(Feed, Feed.id == Article.feed_id)
                .outerjoin(
                    ArticleState,
                    and_(ArticleState.article_id == Article.id, ArticleState.user_id == str(user_id)),
                )
                .where(
                    KeywordStreamMatch.stream_id == stream.id,
                    Feed.owner_id == user_id,
                    KeywordStreamMatch.matched_at >= threshold,
                )
            )
            rows = rows_result.all()
            matched_count = len(rows)
            unread_count = sum(1 for _match, is_read in rows if not bool(is_read))
            latest_match_at = max((_utc_datetime(match.matched_at) for match, _is_read in rows), default=None)
            recent_matches_score = float(matched_count * 10)
            unread_score = float(unread_count * 5)
            priority_score = max(0.0, 10.0 - (float(stream.priority) / 10.0))
            score_breakdown = {
                "recent_matches": recent_matches_score,
                "unread_matches": unread_score,
                "stream_priority": priority_score,
            }
            signal_score = round(sum(score_breakdown.values()), 4)
            stream_items.append(
                DashboardMonitoringSignalStreamOut(
                    stream_id=stream.id,
                    stream_name=stream.name,
                    signal_score=signal_score,
                    matched_count_window=matched_count,
                    unread_count_window=unread_count,
                    confidence_summary={"average_confidence": None, "classifier_run_count": 0},
                    latest_match_at=latest_match_at,
                    score_breakdown=score_breakdown,
                )
            )
        stream_items.sort(
            key=lambda item: (item.signal_score, item.latest_match_at or datetime.min.replace(tzinfo=UTC)), reverse=True
        )
        return DashboardMonitoringSignalsOut(
            status="ready",
            reason=None,
            dependency_spec=None,
            last_updated_at=now,
            window_hours=window_hours,
            streams=stream_items,
        )

    async def _get_profile_row(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
    ) -> UserPrioritizationProfile | None:
        result = await session.execute(
            select(UserPrioritizationProfile).where(UserPrioritizationProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()


dashboard_service = DashboardService()
