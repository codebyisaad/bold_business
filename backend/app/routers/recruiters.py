from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_recruiter
from app.db import get_session
from app.domain.schemas import RecruiterOut
from app.models import Recruiter
from app.repositories.recruiters import list_recruiters

router = APIRouter(prefix="/api/v1/recruiters", tags=["recruiters"])


@router.get("", response_model=list[RecruiterOut])
def read_recruiters(
    recruiter: Annotated[Recruiter, Depends(require_recruiter)],
    session: Annotated[Session, Depends(get_session)],
) -> list[RecruiterOut]:
    """The roster for the switcher; any known recruiter may read it. DECISIONS.md 14."""
    return [RecruiterOut.model_validate(r) for r in list_recruiters(session)]
