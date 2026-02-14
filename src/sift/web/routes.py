from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.session import get_db_session
from sift.services.feed_service import feed_service

router = APIRouter()
templates = Jinja2Templates(directory="src/sift/web/templates")


@router.get("/")
async def home(request: Request, session: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    feeds = await feed_service.list_feeds(session)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"feeds": feeds, "title": "Sift"},
    )

