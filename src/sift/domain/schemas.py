from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class FeedCreate(BaseModel):
    title: str
    url: HttpUrl
    site_url: HttpUrl | None = None


class FeedOut(BaseModel):
    id: UUID
    title: str
    url: str
    site_url: str | None
    is_active: bool
    fetch_interval_minutes: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

