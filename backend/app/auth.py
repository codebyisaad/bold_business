"""Who is calling: the X-Recruiter-Id header, checked against the recruiters table.
No header is 401; an unknown recruiter is 403. Never falls back to anything."""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Recruiter


def require_recruiter(
    session: Annotated[Session, Depends(get_session)],
    x_recruiter_id: Annotated[str | None, Header()] = None,
) -> Recruiter:
    if not x_recruiter_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Recruiter-Id header is required")
    recruiter = session.scalar(select(Recruiter).where(Recruiter.recruiter_id == x_recruiter_id))
    if recruiter is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "unknown recruiter")
    # Row-level security reads this for the rest of the request's transaction.
    session.execute(select(func.set_config("app.recruiter_id", recruiter.recruiter_id, True)))
    return recruiter


def require_admin(recruiter: Annotated[Recruiter, Depends(require_recruiter)]) -> Recruiter:
    if recruiter.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only an admin can do this")
    return recruiter
