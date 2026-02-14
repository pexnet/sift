from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import OpmlImportResult
from sift.services.opml_service import OpmlParseError, opml_service

router = APIRouter()


@router.post("/opml", response_model=OpmlImportResult)
async def import_opml(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OpmlImportResult:
    filename = (file.filename or "").lower()
    if filename and not filename.endswith((".opml", ".xml")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected an .opml or .xml file",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        return await opml_service.import_from_bytes(
            session=session,
            user_id=current_user.id,
            content=content,
        )
    except OpmlParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

