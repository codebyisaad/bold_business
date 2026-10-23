"""GET /api/v1/candidates and /api/v1/recruiters, and row-level security on its own.
Real test database, loaded through the real import. Numbers are the ones in DECISIONS.md."""
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Candidate

CSV_BYTES = (Path(__file__).resolve().parents[2] / "candidates_import.csv").read_bytes()
URL = "/api/v1/candidates"


@pytest.fixture
def loaded(client):
    response = client.post(f"{URL}/import", headers={"X-Recruiter-Id": "R-101"},
                           files={"file": ("candidates.csv", CSV_BYTES, "text/csv")})
    assert response.status_code == 200
    return client


def get(client, recruiter_id, **params):
    headers = {"X-Recruiter-Id": recruiter_id} if recruiter_id else {}
    return client.get(URL, headers=headers, params=params)


def ids(response):
    return [c["candidate_id"] for c in response.json()["items"]]


# --- Scope ----------------------------------------------------------------------------

@pytest.mark.parametrize("recruiter_id, expected", [
    ("R-101", 41),  # Dana, admin
    ("R-102", 19),  # Caleb, US-MW + US-NE
    ("R-103", 9),   # Marisol, PH-MNL + CO-BOG
    ("R-104", 13),  # Jordan, US-W + US-SE
    ("R-105", 8),   # Tessa, US-NE
])
def test_each_recruiter_sees_their_regions(loaded, recruiter_id, expected):
    response = get(loaded, recruiter_id, page_size=100)
    assert response.status_code == 200
    assert response.json()["total"] == expected
    assert len(response.json()["items"]) == expected


def test_items_are_only_from_the_recruiters_regions(loaded):
    regions = {c["region_code"] for c in get(loaded, "R-103", page_size=100).json()["items"]}
    assert regions == {"PH-MNL", "CO-BOG"}


def test_recruiter_cannot_retrieve_a_candidate_outside_their_regions(loaded):
    # C-1001 Alicia Trent is US-MW. Marisol (PH-MNL, CO-BOG) must not get her; Dana must.
    assert get(loaded, "R-103", search="Alicia Trent").json()["total"] == 0
    assert ids(get(loaded, "R-101", search="Alicia Trent")) == ["C-1001"]


@pytest.mark.parametrize("headers, code", [({}, 401), ({"X-Recruiter-Id": "R-999"}, 403)])
def test_missing_or_unknown_recruiter_never_falls_back(loaded, headers, code):
    assert loaded.get(URL, headers=headers).status_code == code
    assert loaded.get("/api/v1/recruiters", headers=headers).status_code == code


# --- Row-level security, with no WHERE clause at all ----------------------------------

def test_rls_returns_nothing_when_no_recruiter_is_set(loaded, db):
    with Session(db) as session:
        assert session.execute(select(func.count()).select_from(Candidate)).scalar_one() == 0


@pytest.mark.parametrize("recruiter_id, expected", [("R-101", 41), ("R-103", 9), ("R-999", 0)])
def test_rls_alone_scopes_an_unfiltered_query(loaded, db, recruiter_id, expected):
    with Session(db) as session:
        session.execute(select(func.set_config("app.recruiter_id", recruiter_id, True)))
        rows = session.execute(select(Candidate)).scalars().all()
    assert len(rows) == expected
    if recruiter_id == "R-103":
        assert {c.region_code for c in rows} == {"PH-MNL", "CO-BOG"}


# --- Search and status ------------------------------------------------------------------

@pytest.mark.parametrize("search, expected", [
    ("Alicia Trent", ["C-1001"]),
    ("alicia trent", ["C-1001"]),
    ("TRENT", ["C-1001"]),
    ("hweiss@protonmail", ["C-1005"]),
    ("Nguyễn", ["C-1008"]),
    ("%", []),   # taken literally, not as a wildcard
    ("_", []),
])
def test_search_matches_full_name_or_email(loaded, search, expected):
    assert ids(get(loaded, "R-101", search=search)) == expected


def test_search_never_widens_the_scope(loaded):
    # Sofía Cárdenas (C-1010) is CO-BOG: visible to Marisol, not to Caleb.
    assert ids(get(loaded, "R-103", search="Sofía")) == ["C-1010"]
    assert ids(get(loaded, "R-102", search="Sofía")) == []


def test_status_filter_narrows_within_scope(loaded):
    assert get(loaded, "R-101", status="interviewing").json()["total"] == 5
    assert get(loaded, "R-101", status="withdrawn").json()["total"] == 1
    caleb = get(loaded, "R-102", status="interviewing", page_size=100).json()
    assert {c["region_code"] for c in caleb["items"]} <= {"US-MW", "US-NE"}
    assert all(c["status"] == "interviewing" for c in caleb["items"])


def test_unknown_status_is_422(loaded):
    assert get(loaded, "R-101", status="on hold").status_code == 422


# --- Paging, order and shape ------------------------------------------------------------

def test_pages_are_25_by_default_ordered_by_id(loaded):
    first, second = get(loaded, "R-101").json(), get(loaded, "R-101", page=2).json()
    assert (first["page_size"], first["total"], len(first["items"]), len(second["items"])) == (25, 41, 25, 16)
    all_ids = [c["candidate_id"] for c in first["items"] + second["items"]]
    assert all_ids == sorted(all_ids) and len(set(all_ids)) == 41
    assert all_ids[0] == "C-1001"


def test_page_past_the_end_is_empty(loaded):
    body = get(loaded, "R-101", page=3).json()
    assert (body["items"], body["total"]) == ([], 41)


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_invalid_paging_is_422(loaded, params):
    assert get(loaded, "R-101", **params).status_code == 422


def test_candidate_shape_uses_iso_dates_and_decimal_strings(loaded):
    alicia = get(loaded, "R-101", search="Alicia Trent").json()["items"][0]
    assert alicia == {
        "candidate_id": "C-1001", "first_name": "Alicia", "last_name": "Trent",
        "email": "alicia.trent@gmail.com", "region_code": "US-MW", "desired_role": "Full-Stack Engineer",
        "status": "active",
        "salary_expectation": "95000.00", "applied_date": "2026-05-14",
    }


# --- Recruiters -----------------------------------------------------------------------

def test_recruiter_list_has_everyone_without_emails(loaded):
    response = loaded.get("/api/v1/recruiters", headers={"X-Recruiter-Id": "R-102"})
    assert response.status_code == 200
    assert [r["recruiter_id"] for r in response.json()] == ["R-101", "R-102", "R-103", "R-104", "R-105"]
    assert response.json()[1] == {
        "recruiter_id": "R-102", "full_name": "Caleb Nguyen", "role": "recruiter",
        "assigned_regions": ["US-MW", "US-NE"],
    }
    assert all("email" not in r for r in response.json())
