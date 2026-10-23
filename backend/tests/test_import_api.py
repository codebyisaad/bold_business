"""POST /api/v1/candidates/import and the writer, against the real test database.
Expected numbers are the ones in DECISIONS.md. The code under test runs as the app role;
assertions read the table as the owner, which row-level security does not apply to."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import event, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.importer import parse_csv, plan_import
from app.models import Candidate
from app.repositories import candidates as repo

CSV_BYTES = (Path(__file__).resolve().parents[2] / "candidates_import.csv").read_bytes()
URL = "/api/v1/candidates/import"
ADMIN = {"X-Recruiter-Id": "R-101"}


def upload(client, data=CSV_BYTES, headers=ADMIN):
    return client.post(URL, headers=headers, files={"file": ("candidates.csv", data, "text/csv")})


def counts(response):
    body = response.json()
    return body["imported"], body["merged"], body["updated"], len(body["rejected"])


def stored(engine, candidate_id):
    with engine.connect() as conn:
        return conn.execute(select(Candidate).where(Candidate.candidate_id == candidate_id)).one()


def total(engine):
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(Candidate)).scalar_one()


def grouped(engine, col):
    with engine.connect() as conn:
        return dict(conn.execute(select(col, func.count()).group_by(col)).all())


@pytest.fixture
def count_inserts(db):
    statements = []

    def record(conn, cursor, statement, *args):
        if statement.startswith("INSERT INTO candidates"):
            statements.append(statement)

    event.listen(db, "before_cursor_execute", record)
    yield statements
    event.remove(db, "before_cursor_execute", record)


# --- The report and what is stored ---------------------------------------------------

def test_first_import(client, owner_engine):
    response = upload(client)
    assert response.status_code == 200
    assert counts(response) == (41, 3, 0, 9)
    assert [r["row"] for r in response.json()["rejected"]] == [35, 36, 37, 42, 47, 49, 50, 53, 54]
    assert response.json()["rejected"][7] == {"row": 53, "reason": "candidate_id C-1010 already belongs to row 11"}
    assert total(owner_engine) == 41


def test_stored_counts_per_region_and_status(client, owner_engine):
    upload(client)
    assert grouped(owner_engine, Candidate.region_code) == {
        "US-MW": 11, "US-NE": 8, "US-W": 8, "US-SE": 5, "PH-MNL": 5, "CO-BOG": 4}
    assert grouped(owner_engine, Candidate.status) == {"active": 30, "interviewing": 5, "screening": 5, "withdrawn": 1}


def test_reimport_counts_every_stored_candidate_as_updated(client, owner_engine):
    upload(client)
    response = upload(client)
    assert counts(response) == (0, 3, 41, 9)
    assert total(owner_engine) == 41


def test_reimport_only_fills_blanks_and_keeps_the_stored_id(client, owner_engine):
    upload(client)
    with owner_engine.begin() as conn:
        conn.execute(update(Candidate).where(Candidate.candidate_id == "C-1016")
                     .values(notes=None, phone=None, salary_expectation=Decimal("1")))
        conn.execute(update(Candidate).where(Candidate.candidate_id == "C-1001").values(candidate_id="C-0001"))

    assert counts(upload(client)) == (0, 3, 41, 9)

    amara = stored(owner_engine, "C-1016")
    assert amara.notes == "Which record wins?"          # was blank: filled
    assert amara.phone == "+19175550125"                # was blank: filled
    assert amara.salary_expectation == Decimal("1.00")  # had a value: kept
    assert stored(owner_engine, "C-0001").email == "alicia.trent@gmail.com"
    with owner_engine.connect() as conn:
        assert conn.execute(select(Candidate).where(Candidate.candidate_id == "C-1001")).first() is None


def test_normalized_values_are_stored(client, owner_engine):
    upload(client)
    assert stored(owner_engine, "C-1038").applied_date == date(2026, 6, 30)
    assert stored(owner_engine, "C-1039").applied_date == date(2026, 5, 14)
    assert stored(owner_engine, "C-1041").applied_date is None
    assert stored(owner_engine, "C-1046").salary_expectation == Decimal("85000.00")
    assert stored(owner_engine, "C-1044").region_code == "US-W"
    assert stored(owner_engine, "C-1001").phone == "+17345550142"
    assert (stored(owner_engine, "C-1001").source, stored(owner_engine, "C-1016").notes) == ("LinkedIn", "Which record wins?")


def test_hostile_rows_are_stored_verbatim_and_the_table_survives(client, owner_engine):
    upload(client)
    assert stored(owner_engine, "C-1036").last_name == "O'Connor'); DROP TABLE candidates;--"
    assert stored(owner_engine, "C-1037").notes == "' OR '1'='1"
    assert total(owner_engine) == 41


def test_unicode_and_multiline_values_round_trip(client, owner_engine):
    upload(client)
    assert (stored(owner_engine, "C-1008").first_name, stored(owner_engine, "C-1008").last_name) == ("Nguyễn", "Thị Hoa")
    assert stored(owner_engine, "C-1050").notes == "Interview notes:\nRound 1 passed.\nRound 2 pending scheduling."


# --- Batching and all-or-nothing ------------------------------------------------------

def test_writes_are_batched(client, count_inserts, monkeypatch):
    monkeypatch.setattr(repo, "BATCH_SIZE", 10)
    upload(client)
    assert len(count_inserts) == 5  # 41 rows in batches of 10


def test_a_database_error_rolls_back_the_whole_file(db, owner_engine, count_inserts, monkeypatch):
    monkeypatch.setattr(repo, "BATCH_SIZE", 10)
    plan = plan_import(parse_csv(CSV_BYTES), existing=[])
    # Bypass validation to plant a value the schema refuses, in the 4th batch (rows 31-40).
    plan.inserts[35] = plan.inserts[35].model_copy(update={"salary_expectation": Decimal("0")})

    with Session(db) as session:
        session.execute(select(func.set_config("app.recruiter_id", "R-101", True)))  # admin, for RLS
        with pytest.raises(IntegrityError, match="salary_expectation"):
            repo.write_plan(session, plan)
        session.rollback()

    assert len(count_inserts) == 4  # batches 1-3 were sent, the 4th failed
    assert total(owner_engine) == 0


# --- Who may import -------------------------------------------------------------------

@pytest.mark.parametrize("headers, code", [
    ({}, 401),
    ({"X-Recruiter-Id": ""}, 401),
    ({"X-Recruiter-Id": "R-999"}, 403),
    ({"X-Recruiter-Id": "R-102"}, 403),  # Caleb is a recruiter, not an admin
])
def test_only_an_admin_can_import(client, owner_engine, headers, code):
    assert upload(client, headers=headers).status_code == code
    assert total(owner_engine) == 0


# --- Bad uploads ----------------------------------------------------------------------

def test_declared_size_over_the_limit_is_refused_before_reading(client, owner_engine, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    response = upload(client, data=b"x" * 70_000)
    assert response.status_code == 413
    assert response.json()["detail"] == "upload is larger than 100 bytes"
    assert total(owner_engine) == 0


def test_file_size_over_the_limit_is_refused(client, owner_engine, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    response = upload(client, data=CSV_BYTES[:500])
    assert response.status_code == 413
    assert response.json()["detail"] == "file is larger than 100 bytes"
    assert total(owner_engine) == 0


def test_bad_file_is_refused_whole(client, owner_engine):
    response = upload(client, data=b"name,mail\nAda,ada@gmail.com\n")
    assert response.status_code == 400
    assert response.json()["detail"].startswith("header must be exactly the 12 candidate columns")
    assert total(owner_engine) == 0


def test_missing_file_field_is_refused(client, owner_engine):
    response = client.post(URL, headers=ADMIN, data={"not_file": "x"})
    assert response.status_code == 400
    assert response.json()["detail"] == "send the CSV as multipart field 'file'"
