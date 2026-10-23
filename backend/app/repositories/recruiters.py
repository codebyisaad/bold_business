from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recruiter


def list_recruiters(session: Session) -> list[Recruiter]:
    return list(session.execute(select(Recruiter).order_by(Recruiter.recruiter_id)).scalars())
