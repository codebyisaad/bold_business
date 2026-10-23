"""DECISIONS.md sections 2-7, one case per rule. Pure, no database."""
from datetime import date
from decimal import Decimal

import pytest

from app.domain import normalize
from app.domain.normalize import Region, Status


@pytest.mark.parametrize("raw, expected", [
    ("  Alicia.Trent@Gmail.com ", "alicia.trent@gmail.com"),
    ("m.bellamy@outlook.com", "m.bellamy@outlook.com"),
])
def test_email_is_trimmed_and_lowercased(raw, expected):
    assert normalize.email(raw) == expected


@pytest.mark.parametrize("raw", ["marcus.reed[at]gmail.com", "tina.holloway.gmail.com", "a@b", "a b@gmail.com"])
def test_invalid_email_is_rejected(raw):
    with pytest.raises(ValueError, match="is not a valid address"):
        normalize.email(raw)


@pytest.mark.parametrize("raw, expected", [
    ("US-MW", Region.US_MW),
    ("us-mw", Region.US_MW),
    (" CO-BOG ", Region.CO_BOG),
    ("USW", Region.US_W),
    ("ph mnl", Region.PH_MNL),
])
def test_region_resolves_to_canonical_code(raw, expected):
    assert normalize.region(raw) is expected


@pytest.mark.parametrize("raw", ["ZZ-99", "US", "US-MWX", "USMW1"])
def test_unknown_region_is_rejected(raw):
    with pytest.raises(ValueError, match="is not a known region"):
        normalize.region(raw)


@pytest.mark.parametrize("raw, expected", [
    ("Active", Status.ACTIVE),
    ("ACTIVE", Status.ACTIVE),
    (" Interviewing ", Status.INTERVIEWING),
    ("hired", Status.HIRED),
    ("Rejected", Status.REJECTED),
])
def test_status_ignores_case_and_surrounding_spaces(raw, expected):
    assert normalize.status(raw) is expected


@pytest.mark.parametrize("raw", ["actve", "on hold", "on-hold", "act ive"])
def test_status_outside_the_enum_is_rejected(raw):
    with pytest.raises(ValueError, match="is not one of"):
        normalize.status(raw)


@pytest.mark.parametrize("raw, expected", [
    ("2026-05-14", date(2026, 5, 14)),
    ("06/30/2026", date(2026, 6, 30)),
    ("14-May-2026", date(2026, 5, 14)),
    ("14-may-2026", date(2026, 5, 14)),
    ("", None),
    ("   ", None),
])
def test_accepted_date_formats_convert_to_a_date(raw, expected):
    assert normalize.applied_date(raw) == expected


@pytest.mark.parametrize("raw, reason", [
    ("2026-02-30", "is not a real calendar date"),
    ("02/30/2026", "is not a real calendar date"),
    ("6/30/2026", "is not YYYY-MM-DD"),
    ("2026-5-14", "is not YYYY-MM-DD"),
    ("2026/05/14", "is not YYYY-MM-DD"),
    ("14-Mai-2026", "is not YYYY-MM-DD"),
    ("yesterday", "is not YYYY-MM-DD"),
])
def test_invalid_date_is_rejected(raw, reason):
    with pytest.raises(ValueError, match=reason):
        normalize.applied_date(raw)


@pytest.mark.parametrize("raw, expected", [
    ("88000", Decimal("88000.00")),
    ("$95,000", Decimal("95000.00")),
    ("97,500", Decimal("97500.00")),
    ("85k", Decimal("85000.00")),
    ("85.5K", Decimal("85500.00")),
    ("$ 1 000", Decimal("1000.00")),
    ("95000.005", Decimal("95000.01")),
    ("95000.004", Decimal("95000.00")),
    ("10000000", Decimal("10000000.00")),
])
def test_salary_parses_to_two_decimals(raw, expected):
    assert normalize.salary(raw) == expected


@pytest.mark.parametrize("raw", ["", "  ", "negotiable", "Negotiable", "NA", "n/a", "N/A", "tbd", "TBD"])
def test_blank_or_placeholder_salary_is_null(raw):
    assert normalize.salary(raw) is None


@pytest.mark.parametrize("raw, reason", [
    ("0", "must be greater than zero"),
    ("0.004", "must be greater than zero"),
    ("-5", "must be greater than zero"),
    ("10000000.01", "is above 10,000,000"),
    ("10001k", "is above 10,000,000"),
    ("abc", "is not a number"),
    ("1e5", "is not a number"),
    ("unknown", "is not a number"),
])
def test_invalid_salary_is_rejected(raw, reason):
    with pytest.raises(ValueError, match=reason):
        normalize.salary(raw)


@pytest.mark.parametrize("raw, expected", [
    ("+1 (734) 555-0142", "+17345550142"),
    ("734-555-0187", "+17345550187"),
    ("(312) 555-0165", "+13125550165"),
    ("616.555.0134", "+16165550134"),
    ("+57 601 555 0177", "+576015550177"),
    ("+63 917 555 0122", "+639175550122"),
    ("", None),
])
def test_phone_is_normalized_to_e164(raw, expected):
    assert normalize.phone(raw) == expected


@pytest.mark.parametrize("raw, reason", [
    ("555-0142", r"needs a \+country code or exactly 10 digits"),
    ("1-734-555-0142", r"needs a \+country code or exactly 10 digits"),
    ("+1 734 555 0142 ext 5", "contains characters other than"),
    ("+12345", "must have 8 to 15 digits"),
])
def test_invalid_phone_is_rejected(raw, reason):
    with pytest.raises(ValueError, match=reason):
        normalize.phone(raw)


@pytest.mark.parametrize("raw, expected", [
    ("  Full-Stack   Engineer ", "Full-Stack Engineer"),
    ("O'Connor", "O'Connor"),
    ("Nguyễn", "Nguyễn"),
    ("   ", None),
])
def test_collapse_trims_without_changing_case(raw, expected):
    assert normalize.collapse(raw) == expected
