"""Load the two provided CSVs into the app database (run after `python -m app.db`):
    uv run python -m app.seed

Recruiters are written as techforce_owner (the app role can only read them) and follow
DECISIONS.md section 13. Candidates go through exactly the same parse -> plan -> write path
as POST /api/v1/candidates/import.
"""
import csv
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import SessionLocal
from app.domain.importer import parse_csv
from app.models import Recruiter
from app.repositories.candidates import import_rows

ROOT = Path(__file__).resolve().parents[2]
RECRUITERS_CSV = ROOT / "recruiters.csv"
CANDIDATES_CSV = ROOT / "candidates_import.csv"


def read_recruiters(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [
            {
                "recruiter_id": row["recruiter_id"],
                "full_name": row["full_name"],
                "email": row["email"],
                "role": row["role"],
                "assigned_regions": row["assigned_regions"].split("|"),
            }
            for row in csv.DictReader(fh)
        ]


def load_recruiters(owner_url: str, path: Path = RECRUITERS_CSV) -> int:
    """Upsert the roster by recruiter_id in one transaction. The schema's CHECKs reject
    any non-canonical value, which fails the whole load."""
    rows = read_recruiters(path)
    stmt = insert(Recruiter).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Recruiter.recruiter_id],
        set_={col: getattr(stmt.excluded, col) for col in ("full_name", "email", "role", "assigned_regions")},
    )
    owner_engine = create_engine(owner_url)
    try:
        with owner_engine.begin() as conn:
            conn.execute(stmt)
    finally:
        owner_engine.dispose()
    return len(rows)


if __name__ == "__main__":
    print(f"recruiters loaded: {load_recruiters(settings.owner_database_url)}")
    with SessionLocal() as session:
        report = import_rows(session, parse_csv(CANDIDATES_CSV.read_bytes()))
    print(f"candidates: imported={report.imported} merged={report.merged} "
          f"updated={report.updated} rejected={len(report.rejected)}")
    for rejected in report.rejected:
        print(f"  row {rejected.row}: {rejected.reason}")
