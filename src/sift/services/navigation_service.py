from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, ArticleState, Feed, FeedFolder, KeywordStream, KeywordStreamMatch
from sift.domain.schemas import (
    NavigationFeedNodeOut,
    NavigationFolderNodeOut,
    NavigationStreamNodeOut,
    NavigationSystemNodeOut,
    NavigationTreeOut,
)


class NavigationService:
    async def get_navigation_tree(self, *, session: AsyncSession, user_id: UUID) -> NavigationTreeOut:
        now = datetime.now(UTC)
        unread_expr = and_(
            func.coalesce(ArticleState.is_read, False).is_(False),
            func.coalesce(ArticleState.is_archived, False).is_(False),
        )
        archived_expr = func.coalesce(ArticleState.is_archived, False).is_(True)
        starred_expr = and_(
            func.coalesce(ArticleState.is_starred, False).is_(True),
            func.coalesce(ArticleState.is_archived, False).is_(False),
        )
        recent_expr = and_(
            func.coalesce(ArticleState.is_read, False).is_(True),
            func.coalesce(ArticleState.updated_at, Article.created_at) >= now - timedelta(days=7),
        )
        fresh_expr = and_(
            unread_expr,
            func.coalesce(Article.published_at, Article.created_at) >= now - timedelta(days=3),
        )

        systems_count_query = (
            select(
                func.count().label("total"),
                func.sum(case((unread_expr, 1), else_=0)).label("unread"),
                func.sum(case((starred_expr, 1), else_=0)).label("saved"),
                func.sum(case((archived_expr, 1), else_=0)).label("archived"),
                func.sum(case((recent_expr, 1), else_=0)).label("recent"),
                func.sum(case((fresh_expr, 1), else_=0)).label("fresh"),
            )
            .select_from(Article)
            .join(Feed, Feed.id == Article.feed_id)
            .outerjoin(
                ArticleState,
                and_(ArticleState.article_id == Article.id, ArticleState.user_id == str(user_id)),
            )
            .where(Feed.owner_id == user_id)
        )
        systems_row = (await session.execute(systems_count_query)).one()
        systems = [
            NavigationSystemNodeOut(key="all", title="All articles", unread_count=int(systems_row.unread or 0)),
            NavigationSystemNodeOut(key="fresh", title="Fresh articles", unread_count=int(systems_row.fresh or 0)),
            NavigationSystemNodeOut(key="saved", title="Saved", unread_count=int(systems_row.saved or 0)),
            NavigationSystemNodeOut(key="archived", title="Archived", unread_count=int(systems_row.archived or 0)),
            NavigationSystemNodeOut(key="recent", title="Recently read", unread_count=int(systems_row.recent or 0)),
        ]

        feed_rows = (
            await session.execute(
                select(Feed.id, Feed.title, Feed.folder_id)
                .where(Feed.owner_id == user_id, Feed.is_archived.is_(False))
                .order_by(Feed.title.asc())
            )
        ).all()
        unread_by_feed_rows = (
            await session.execute(
                select(
                    Article.feed_id,
                    func.sum(case((unread_expr, 1), else_=0)).label("unread"),
                )
                .select_from(Article)
                .join(Feed, Feed.id == Article.feed_id)
                .outerjoin(
                    ArticleState,
                    and_(ArticleState.article_id == Article.id, ArticleState.user_id == str(user_id)),
                )
                .where(Feed.owner_id == user_id)
                .where(Feed.is_archived.is_(False))
                .group_by(Article.feed_id)
            )
        ).all()
        unread_by_feed = {feed_id: int(unread or 0) for feed_id, unread in unread_by_feed_rows}

        folder_rows = (
            await session.execute(
                select(FeedFolder.id, FeedFolder.name)
                .where(FeedFolder.user_id == user_id)
                .order_by(FeedFolder.sort_order.asc(), FeedFolder.name.asc())
            )
        ).all()

        folder_nodes: list[NavigationFolderNodeOut] = []
        feeds_by_folder: dict[UUID | None, list[NavigationFeedNodeOut]] = {}
        for feed_id, title, folder_id in feed_rows:
            feeds_by_folder.setdefault(folder_id, []).append(
                NavigationFeedNodeOut(id=feed_id, title=title, unread_count=unread_by_feed.get(feed_id, 0))
            )

        for folder_id, folder_name in folder_rows:
            children = feeds_by_folder.get(folder_id, [])
            folder_nodes.append(
                NavigationFolderNodeOut(
                    id=folder_id,
                    name=folder_name,
                    unread_count=sum(node.unread_count for node in children),
                    feeds=children,
                )
            )

        unfiled_children = feeds_by_folder.get(None, [])
        if unfiled_children:
            folder_nodes.append(
                NavigationFolderNodeOut(
                    id=None,
                    name="Unfiled",
                    unread_count=sum(node.unread_count for node in unfiled_children),
                    feeds=unfiled_children,
                )
            )

        stream_rows = (
            await session.execute(
                select(
                    KeywordStream.id,
                    KeywordStream.name,
                    func.sum(case((and_(KeywordStreamMatch.article_id.is_not(None), unread_expr), 1), else_=0)).label(
                        "unread"
                    ),
                )
                .select_from(KeywordStream)
                .outerjoin(KeywordStreamMatch, KeywordStreamMatch.stream_id == KeywordStream.id)
                .outerjoin(Article, Article.id == KeywordStreamMatch.article_id)
                .outerjoin(
                    ArticleState,
                    and_(ArticleState.article_id == Article.id, ArticleState.user_id == str(user_id)),
                )
                .where(KeywordStream.user_id == user_id)
                .group_by(KeywordStream.id, KeywordStream.name)
                .order_by(KeywordStream.priority.asc(), KeywordStream.name.asc())
            )
        ).all()
        streams = [
            NavigationStreamNodeOut(id=stream_id, name=name, unread_count=int(unread or 0))
            for stream_id, name, unread in stream_rows
        ]

        return NavigationTreeOut(systems=systems, folders=folder_nodes, streams=streams)


navigation_service = NavigationService()
