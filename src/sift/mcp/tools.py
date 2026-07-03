"""MCP tool definitions for Sift.

Each tool calls the service layer directly — no HTTP overhead.
All tools receive a user_id (resolved from the API token) and
an async DB session factory.
"""

import json
from typing import Any
from uuid import UUID

from mcp.types import Tool

from sift.db.session import SessionLocal
from sift.services.article_service import article_service
from sift.services.feed_health_service import feed_health_service
from sift.services.feed_service import feed_service
from sift.services.folder_service import folder_service
from sift.services.navigation_service import navigation_service
from sift.services.stream_service import stream_service

# Tool schemas (returned to MCP client during discovery)
TOOL_DEFINITIONS: list[Tool] = [
    Tool(
        name="sift_list_feeds",
        description="List all RSS feeds the user is subscribed to, optionally including archived ones.",
        inputSchema={
            "type": "object",
            "properties": {
                "include_archived": {"type": "boolean", "default": False, "description": "Include archived feeds"},
            },
        },
    ),
    Tool(
        name="sift_search_articles",
        description="Search and list articles with filtering by scope, state, and free-text query.",
        inputSchema={
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Free-text search query"},
                "state": {
                    "type": "string",
                    "enum": ["all", "unread", "saved", "archived", "fresh", "recent"],
                    "default": "all",
                },
                "scope_type": {
                    "type": "string",
                    "enum": ["system", "folder", "feed", "stream"],
                    "default": "system",
                },
                "scope_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Required when scope_type is folder/feed/stream",
                },
                "limit": {"type": "integer", "default": 100, "minimum": 1, "maximum": 500},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
                "sort": {
                    "type": "string",
                    "enum": ["newest", "oldest", "unread_first"],
                    "default": "newest",
                },
            },
        },
    ),
    Tool(
        name="sift_get_article",
        description="Get full details of a single article by ID, including content and fulltext status.",
        inputSchema={
            "type": "object",
            "properties": {
                "article_id": {"type": "string", "format": "uuid", "description": "Article UUID"},
            },
            "required": ["article_id"],
        },
    ),
    Tool(
        name="sift_list_folders",
        description="List all feed folders (catalogs) for the user.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="sift_get_navigation",
        description="Get the full navigation tree: folders, feeds, streams, and unread counts.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="sift_get_feed_health",
        description="Get feed health summary: stale feeds, error feeds, fetch timing, article throughput.",
        inputSchema={
            "type": "object",
            "properties": {
                "lifecycle": {
                    "type": "string",
                    "enum": ["all", "active", "paused", "archived"],
                    "default": "all",
                },
                "error_only": {"type": "boolean", "default": False},
                "stale_only": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200},
            },
        },
    ),
    Tool(
        name="sift_list_streams",
        description="List all keyword monitoring streams for the user.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="sift_add_feed",
        description="Subscribe to a new RSS feed by URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri", "description": "Feed URL"},
                "title": {"type": "string", "description": "Display title for the feed"},
                "folder_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Optional folder to place feed in",
                },
            },
            "required": ["url", "title"],
        },
    ),
    Tool(
        name="sift_mark_articles_read",
        description="Mark articles as read by article IDs (bulk).",
        inputSchema={
            "type": "object",
            "properties": {
                "article_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                    "description": "Article UUIDs to mark read",
                },
            },
            "required": ["article_ids"],
        },
    ),
]


async def execute_tool(name: str, arguments: dict[str, Any], user_id: UUID) -> str:
    """Execute a tool by name and return JSON result string."""
    async with SessionLocal() as session:
        if name == "sift_list_feeds":
            feeds = await feed_service.list_feeds(
                session=session,
                user_id=user_id,
                include_archived=arguments.get("include_archived", False),
            )
            return json.dumps(
                [
                    {
                        "id": str(f.id),
                        "title": f.title,
                        "url": f.url,
                        "is_active": f.is_active,
                        "folder_id": str(f.folder_id) if f.folder_id else None,
                    }
                    for f in feeds
                ]
            )

        elif name == "sift_search_articles":
            scope_id = arguments.get("scope_id")
            result = await article_service.list_articles(
                session=session,
                user_id=user_id,
                scope_type=arguments.get("scope_type", "system"),
                scope_id=UUID(scope_id) if scope_id else None,
                state=arguments.get("state", "all"),
                q=arguments.get("q"),
                limit=arguments.get("limit", 100),
                offset=arguments.get("offset", 0),
                sort=arguments.get("sort", "newest"),
            )
            return result.model_dump_json()

        elif name == "sift_get_article":
            from sift.services.article_service import ArticleNotFoundError

            try:
                detail = await article_service.get_article_detail(
                    session=session,
                    user_id=user_id,
                    article_id=UUID(arguments["article_id"]),
                )
                return detail.model_dump_json()
            except ArticleNotFoundError as exc:
                return json.dumps({"error": str(exc)})

        elif name == "sift_list_folders":
            folders = await folder_service.list_folders(session=session, user_id=user_id)
            return json.dumps([{"id": str(f.id), "name": f.name, "sort_order": f.sort_order} for f in folders])

        elif name == "sift_get_navigation":
            tree = await navigation_service.get_navigation_tree(session=session, user_id=user_id)
            return tree.model_dump_json()

        elif name == "sift_get_feed_health":
            health_result = await feed_health_service.list_feed_health(
                session=session,
                user_id=user_id,
                lifecycle=arguments.get("lifecycle", "all"),
                q=None,
                stale_only=arguments.get("stale_only", False),
                error_only=arguments.get("error_only", False),
                include_all=False,
                limit=arguments.get("limit", 50),
                offset=0,
            )
            return health_result.model_dump_json()

        elif name == "sift_list_streams":
            streams = await stream_service.list_streams(session=session, user_id=user_id)
            return json.dumps([stream_service.to_out(s).model_dump(mode="json") for s in streams])

        elif name == "sift_add_feed":
            from pydantic import HttpUrl

            from sift.domain.schemas import FeedCreate
            from sift.services.feed_service import FeedAlreadyExistsError, FeedFolderNotFoundError

            try:
                feed = await feed_service.create_feed(
                    session=session,
                    user_id=user_id,
                    data=FeedCreate(
                        title=arguments["title"],
                        url=HttpUrl(arguments["url"]),
                        folder_id=UUID(arguments["folder_id"]) if arguments.get("folder_id") else None,
                    ),
                )
                return json.dumps({"id": str(feed.id), "title": feed.title, "url": feed.url})
            except FeedAlreadyExistsError as exc:
                return json.dumps({"error": str(exc)})
            except FeedFolderNotFoundError as exc:
                return json.dumps({"error": str(exc)})

        elif name == "sift_mark_articles_read":
            ids = [UUID(aid) for aid in arguments["article_ids"]]
            count = await article_service.bulk_patch_state(
                session=session,
                user_id=user_id,
                article_ids=ids,
                is_read=True,
                is_starred=None,
                is_archived=None,
            )
            return json.dumps({"updated_count": count})

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
