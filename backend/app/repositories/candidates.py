"""Persisting an import. The decisions are made by app.domain.importer; this module only
reads what it needs and writes the plan. Every statement is a SQLAlchemy expression."""
from collections.abc import Iterator, Sequence
from itertools import batched

from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.domain import normalize
from app.domain.importer import RawRow, plan_import
from app.domain.normalize import Status
from app.domain.schemas import CandidateRow, ImportPlan, ImportReport
from app.models import Candidate, Recruiter

BATCH_SIZE = 500     # 500 rows x 12 columns stays far below Postgres's 65,535 parameters
LOOKUP_SIZE = 1000   # values per IN (...) when reading existing candidates
IMPORT_LOCK_KEY = 7_300_001  # arbitrary constant; one advisory lock shared by all imports

# Only these may change on an existing candidate, and only when blank (DECISIONS.md 8.5).
FILLABLE = ("phone", "desired_role", "salary_expectation", "applied_date", "source", "notes")


def import_rows(session: Session, rows: Sequence[RawRow]) -> ImportReport:
    """Plan and write a parsed file in one transaction. Raises on a database error, and the
    caller's session then rolls everything back."""
    session.execute(select(func.pg_advisory_xact_lock(IMPORT_LOCK_KEY)))
    # Same transformations as normalize.email / normalize.collapse, minus validation:
    # a key that later fails validation just finds nothing.
    emails = {raw["email"].strip().lower() for _, raw in rows}
    ids = {normalize.collapse(raw["candidate_id"]) or "" for _, raw in rows}
    plan = plan_import(rows, existing=load_existing(session, emails, ids))
    inserted, updated = write_plan(session, plan)
    session.commit()
    return ImportReport(
        imported=inserted,
        merged=len(plan.merged),
        updated=updated,
        rejected=sorted(plan.rejected, key=lambda r: r.row),
    )


def visible_to(recruiter_id: str):
    """The scope rule as a query condition (DECISIONS.md 14). Row-level security applies
    the same rule again inside Postgres."""
    return (
        select(Recruiter.recruiter_id)
        .where(
            Recruiter.recruiter_id == recruiter_id,
            or_(Recruiter.role == "admin", Recruiter.assigned_regions.has_key(Candidate.region_code)),
        )
        .exists()
    )


def list_candidates(
    session: Session, recruiter_id: str, *, search: str, status: Status | None, page: int, page_size: int,
) -> tuple[list[Candidate], int]:
    conditions = [visible_to(recruiter_id)]
    if term := search.strip():
        full_name = Candidate.first_name + " " + Candidate.last_name
        conditions.append(or_(full_name.icontains(term, autoescape=True),
                              Candidate.email.icontains(term, autoescape=True)))
    if status is not None:
        conditions.append(Candidate.status == status.value)

    total = session.execute(select(func.count()).select_from(Candidate).where(*conditions)).scalar_one()
    items = session.execute(
        select(Candidate).where(*conditions)
        .order_by(Candidate.candidate_id)
        .limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return list(items), total


def load_existing(session: Session, emails: set[str], ids: set[str]) -> list[tuple[str, str]]:
    """(candidate_id, email) of stored candidates sharing an email or an id with the file."""
    found: set[tuple[str, str]] = set()  # Row objects are tuples
    for chunk in _chunks(sorted(emails), LOOKUP_SIZE):
        found.update(session.execute(
            select(Candidate.candidate_id, Candidate.email).where(Candidate.email.in_(chunk))).all())
    for chunk in _chunks(sorted(ids), LOOKUP_SIZE):
        found.update(session.execute(
            select(Candidate.candidate_id, Candidate.email).where(Candidate.candidate_id.in_(chunk))).all())
    return sorted(found)


def write_plan(session: Session, plan: ImportPlan) -> tuple[int, int]:
    """Upsert inserts and updates in batches. Returns (inserted, updated) as reported by
    Postgres: a row's xmax is 0 when this statement inserted it, non-zero when it updated it."""
    inserted = updated = 0
    for batch in _chunks(plan.inserts + plan.updates, BATCH_SIZE):
        stmt = insert(Candidate).values([_values(c) for c in batch])
        stmt = stmt.on_conflict_do_update(
            index_elements=[Candidate.email],
            set_={col: func.coalesce(getattr(Candidate, col), getattr(stmt.excluded, col)) for col in FILLABLE},
        ).returning((literal_column("xmax") == 0).label("inserted"))
        for was_inserted in session.execute(stmt).scalars():
            if was_inserted:
                inserted += 1
            else:
                updated += 1
    return inserted, updated


def _values(candidate: CandidateRow) -> dict:
    return candidate.model_dump(mode="python") | {
        "region_code": candidate.region_code.value,
        "status": candidate.status.value,
    }


def _chunks[T](items: Sequence[T], size: int) -> Iterator[list[T]]:
    for chunk in batched(items, size):
        yield list(chunk)
