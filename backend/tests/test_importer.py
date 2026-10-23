"""The pure importer against the real candidates_import.csv. No database.
Expected numbers are the ones in DECISIONS.md."""
import csv
import io
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.importer import COLUMNS, BadFileError, parse_csv, plan_import

CSV_PATH = Path(__file__).resolve().parents[2] / "candidates_import.csv"


@pytest.fixture(scope="module")
def rows():
    return parse_csv(CSV_PATH.read_bytes())


@pytest.fixture(scope="module")
def plan(rows):
    return plan_import(rows, existing=[])


@pytest.fixture(scope="module")
def inserted(plan):
    return {c.candidate_id: c for c in plan.inserts}


def make_csv(*rows: dict[str, str], header=COLUMNS) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow([row.get(column, "") for column in header])
    return buffer.getvalue().encode()


def valid_row(**overrides: str) -> dict[str, str]:
    row = {
        "candidate_id": "C-9001", "first_name": "Test", "last_name": "Person",
        "email": "test.person@gmail.com", "region_code": "US-MW", "status": "Active",
    }
    return row | overrides


# --- First import into an empty database --------------------------------------------

def test_file_has_53_candidate_rows_numbered_like_a_spreadsheet(rows):
    assert len(rows) == 53
    assert rows[0][0] == 2 and rows[-1][0] == 54


def test_first_import_counts(plan):
    report = plan.report()
    assert (report.imported, report.merged, report.updated, len(report.rejected)) == (41, 3, 0, 9)


def test_first_import_rejected_rows_and_reasons(plan):
    statuses = "active, screening, interviewing, withdrawn, hired, rejected"
    assert [(r.row, r.reason) for r in plan.report().rejected] == [
        (35, "email 'marcus.reed[at]gmail.com' is not a valid address"),
        (36, "email 'tina.holloway.gmail.com' is not a valid address"),
        (37, "email is missing"),
        (42, "applied_date '2026-02-30' is not a real calendar date"),
        (47, "region_code 'ZZ-99' is not a known region"),
        (49, f"status 'actve' is not one of: {statuses}"),
        (50, f"status 'on hold' is not one of: {statuses}"),
        (53, "candidate_id C-1010 already belongs to row 11"),
        (54, "region_code is missing"),
    ]


def test_merged_rows_point_at_the_row_they_fold_into(plan):
    assert [(m.row, m.into_row) for m in plan.merged] == [(32, 5), (33, 2), (34, 17)]


def test_alicia_keeps_her_original_id_and_source(inserted):
    alicia = [c for c in inserted.values() if c.email == "alicia.trent@gmail.com"]
    assert len(alicia) == 1
    assert alicia[0].candidate_id == "C-1001"
    assert alicia[0].source == "LinkedIn"
    assert alicia[0].notes == "Strong React portfolio"
    assert "C-1031" not in inserted


def test_amara_only_gets_her_blank_notes_filled(inserted):
    amara = inserted["C-1016"]
    assert amara.first_name == "Amara"
    assert amara.phone == "+19175550125"
    assert amara.salary_expectation == Decimal("108000.00")
    assert amara.applied_date == date(2026, 6, 4)
    assert amara.notes == "Which record wins?"
    assert "C-1032" not in inserted


def test_exact_duplicate_is_stored_once(plan):
    assert [c.candidate_id for c in plan.inserts].count("C-1004") == 1


def test_id_collision_keeps_the_first_owner(inserted):
    assert inserted["C-1010"].first_name == "Sofía"
    assert all(c.email != "becca.storm@gmail.com" for c in inserted.values())


def test_counts_per_region(plan):
    assert Counter(c.region_code.value for c in plan.inserts) == {
        "US-MW": 11, "US-NE": 8, "US-W": 8, "US-SE": 5, "PH-MNL": 5, "CO-BOG": 4}


def test_counts_per_status(plan):
    assert Counter(c.status.value for c in plan.inserts) == {
        "active": 30, "interviewing": 5, "screening": 5, "withdrawn": 1}


def test_messy_values_are_normalized(inserted):
    assert inserted["C-1038"].applied_date == date(2026, 6, 30)
    assert inserted["C-1039"].applied_date == date(2026, 5, 14)
    assert inserted["C-1041"].applied_date is None
    assert inserted["C-1042"].region_code.value == "US-MW"
    assert inserted["C-1043"].region_code.value == "CO-BOG"
    assert inserted["C-1044"].region_code.value == "US-W"
    assert inserted["C-1046"].status.value == "active"
    assert inserted["C-1046"].salary_expectation == Decimal("85000.00")
    assert inserted["C-1001"].phone == "+17345550142"


def test_hostile_rows_are_kept_as_literal_text(inserted):
    assert inserted["C-1036"].last_name == "O'Connor'); DROP TABLE candidates;--"
    assert inserted["C-1037"].notes == "' OR '1'='1"


def test_unicode_and_multiline_values_survive(inserted):
    assert (inserted["C-1008"].first_name, inserted["C-1008"].last_name) == ("Nguyễn", "Thị Hoa")
    assert inserted["C-1044"].last_name == "Trần"
    assert inserted["C-1050"].notes == "Interview notes:\nRound 1 passed.\nRound 2 pending scheduling."


# --- Same file again, with the first import already stored -------------------------

def test_reimport_updates_every_stored_candidate(rows, plan):
    stored = [(c.candidate_id, c.email) for c in plan.inserts]
    report = plan_import(rows, existing=stored).report()
    assert (report.imported, report.merged, report.updated, len(report.rejected)) == (0, 3, 41, 9)


def test_stored_id_owned_by_another_email_rejects_the_row(rows):
    plan = plan_import(rows, existing=[("C-1001", "someone.else@gmail.com")])
    report = plan.report()
    assert report.rejected[0].row == 2
    assert report.rejected[0].reason == "candidate_id C-1001 already belongs to a different candidate"
    assert (report.imported, report.merged, len(report.rejected)) == (41, 2, 10)
    # Row 2 is out, so row 33 is now the first kept row with Alicia's email.
    alicia = next(c for c in plan.inserts if c.email == "alicia.trent@gmail.com")
    assert (alicia.candidate_id, alicia.source) == ("C-1031", "Indeed")


def test_same_email_stored_under_another_id_is_an_update(rows):
    plan = plan_import(rows, existing=[("C-0001", "alicia.trent@gmail.com")])
    assert [c.email for c in plan.updates] == ["alicia.trent@gmail.com"]
    assert plan.report().imported == 40


# --- Synthetic rows -----------------------------------------------------------------

def test_row_with_several_problems_lists_every_reason():
    data = make_csv(valid_row(email="bad", status="on hold", salary_expectation="lots"))
    report = plan_import(parse_csv(data), existing=[]).report()
    assert report.rejected[0].row == 2
    assert report.rejected[0].reason == (
        "email 'bad' is not a valid address; "
        "salary 'lots' is not a number; "
        "status 'on hold' is not one of: active, screening, interviewing, withdrawn, hired, rejected")


def test_every_missing_required_field_is_named():
    data = make_csv({"phone": "734-555-0187"})
    reason = plan_import(parse_csv(data), existing=[]).report().rejected[0].reason
    for field in ("candidate_id", "first_name", "last_name", "email", "region_code", "status"):
        assert f"{field} is missing" in reason


def test_blank_optional_fields_are_null():
    candidate = plan_import(parse_csv(make_csv(valid_row())), existing=[]).inserts[0]
    assert (candidate.phone, candidate.desired_role, candidate.salary_expectation,
            candidate.applied_date, candidate.source, candidate.notes) == (None,) * 6


# --- Bad files are refused whole ------------------------------------------------------

@pytest.mark.parametrize("data, reason", [
    (b"", "file is empty"),
    (b"\xff\xfe\x00", "file is not valid UTF-8"),
    (make_csv(), "file has a header but no candidate rows"),
    (make_csv(valid_row(), header=COLUMNS[:-1]), "missing notes"),
    (make_csv(valid_row(), header=COLUMNS + ("extra",)), "unexpected extra"),
    (make_csv(valid_row(), header=COLUMNS[:-1] + ("email",)), "duplicated email"),
    (make_csv(valid_row()) + b"C-9002,Only,Three\r\n", "row 3 has 3 fields, expected 12"),
    (make_csv(valid_row()) + b"\r\n", "row 3 has 0 fields, expected 12"),
])
def test_bad_file_is_rejected_whole(data, reason):
    with pytest.raises(BadFileError, match=reason):
        parse_csv(data)


def test_byte_order_mark_is_allowed():
    assert len(parse_csv(b"\xef\xbb\xbf" + make_csv(valid_row()))) == 1
