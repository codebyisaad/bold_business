from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.auth import require_admin, require_recruiter
from app.config import settings
from app.db import get_session
from app.domain.importer import BadFileError, parse_csv
from app.domain.normalize import Status
from app.domain.schemas import CandidateOut, CandidatePage, ImportReport
from app.models import Recruiter
from app.repositories.candidates import import_rows, list_candidates

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])

# Room for the multipart boundary and part headers around the file itself.
MULTIPART_OVERHEAD = 64 * 1024


@router.get("", response_model=CandidatePage)
def read_candidates(
    recruiter: Annotated[Recruiter, Depends(require_recruiter)],
    session: Annotated[Session, Depends(get_session)],
    search: str = "",
    status: Status | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CandidatePage:
    """Candidates in the caller's regions (all of them for an admin). DECISIONS.md 14."""
    items, total = list_candidates(
        session, recruiter.recruiter_id, search=search, status=status, page=page, page_size=page_size)
    return CandidatePage(
        items=[CandidateOut.model_validate(c) for c in items], total=total, page=page, page_size=page_size)


@router.post("/import", response_model=ImportReport)
async def import_candidates(
    request: Request,
    admin: Annotated[Recruiter, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
) -> ImportReport:
    """Upload the CSV as multipart field `file`. Admin only (DECISIONS.md 12).

    The body is parsed here rather than declared as a parameter so that the admin check and
    the declared-size check run before any of the upload is read (DECISIONS.md 10).
    """
    limit = settings.max_upload_bytes
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit + MULTIPART_OVERHEAD:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"upload is larger than {limit} bytes")

    async with request.form(max_files=1, max_fields=1) as form:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "send the CSV as multipart field 'file'")
        if upload.size is None or upload.size > limit:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"file is larger than {limit} bytes")
        data = await upload.read()

    try:
        rows = parse_csv(data)
    except BadFileError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
    return await run_in_threadpool(import_rows, session, rows)
