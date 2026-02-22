import asyncio
from uuid import UUID

from sift.core.runtime import get_plugin_manager
from sift.db.session import SessionLocal
from sift.services.ingestion_service import FeedNotFoundError, ingestion_service


async def _run_ingest(feed_id: UUID) -> dict[str, object]:
    async with SessionLocal() as session:
        result = await ingestion_service.ingest_feed(session, feed_id=feed_id, plugin_manager=get_plugin_manager())
    return result.model_dump(mode="json")


def ingest_feed_job(feed_id: str) -> dict[str, object]:
    try:
        parsed_id = UUID(feed_id)
    except ValueError as exc:
        return {"feed_id": feed_id, "status": "invalid", "errors": [str(exc)]}

    try:
        payload = asyncio.run(_run_ingest(parsed_id))
    except FeedNotFoundError as exc:
        return {"feed_id": feed_id, "status": "missing", "errors": [str(exc)]}

    payload["status"] = "ok"
    return payload
