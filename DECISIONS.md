# Data rules

These are the rules the candidate import follows, one rule per section, so a reviewer can
check behaviour without reading the code. If a case isn't covered here, the code must not
guess. It goes under "Open questions" until it's decided.

## 1. Required and optional fields

- **Required:** `candidate_id`, `first_name`, `last_name`, `email`, `region_code`, `status`.
  A required field counts as missing when it is empty or only whitespace.
- **Optional:** `phone`, `desired_role`, `salary_expectation`, `applied_date`, `source`, `notes`.
  A blank optional field is stored as null (it is absent, not bad data).
- A row missing any required field is rejected. The reason names every missing field.
- A row with several problems is rejected once, and the reason lists every problem.

## 2. Email is the candidate's identity

- The email is trimmed and lowercased, then checked as a real address (syntax only, no DNS
  lookup).
- An invalid or missing email rejects the row.
- Two rows with the same email (after trimming and lowercasing) are the same candidate.

## 3. Regions

- Canonical regions are a fixed list: `US-MW`, `US-NE`, `US-SE`, `US-W`, `PH-MNL`, `CO-BOG`.
- To match, the value is uppercased and everything that isn't a letter or digit is removed.
  It is then compared against the canonical codes with their hyphens removed. So `us-mw`,
  ` CO-BOG ` and `USW` resolve to `US-MW`, `CO-BOG` and `US-W`.
- Nothing fuzzier than that. An unknown code (e.g. `ZZ-99`) or a blank region rejects the row.

## 4. Status

- Status is a fixed list: `active`, `screening`, `interviewing`, `withdrawn`, `hired`,
  `rejected`.
- Matching ignores case and surrounding spaces. There is no spelling correction and no
  invented states, so `actve` and `on hold` are rejected.

## 5. Applied date

- One format everywhere, in the database and in every API response: ISO `YYYY-MM-DD`.
- On the way in, three formats are accepted, each with a two-digit day and month:

  | Format | Example | Notes |
  |---|---|---|
  | `YYYY-MM-DD` | `2026-05-14` | |
  | `MM/DD/YYYY` (US order) | `06/30/2026` | |
  | `DD-Mon-YYYY` | `14-May-2026` | Month name is the 3-letter English abbreviation, any case |

- So `6/30/2026` is rejected.
- A blank date is allowed and stored as null.
- Any other format, or an impossible date such as `2026-02-30`, rejects the row.

## 6. Salary expectation

- Dollar signs, commas and spaces are removed. A trailing `k` or `K` means thousands, so
  `85k` is 85,000.
- A blank value, or one of the words `negotiable`, `na`, `n/a`, `tbd` (any case), is stored
  as null. This is the only case where a non-number becomes null.
- More than two decimal places is rounded half-up to two (`95000.005` becomes `95000.01`).
- After rounding, the row is rejected if the value is not a number, is zero or negative, or
  is above 10,000,000.
- Stored as a numeric value with two decimal places.

## 7. Other text fields

- **First name, last name, desired role and source:** surrounding whitespace is trimmed and
  runs of whitespace inside are collapsed to one space. Case is never changed, so
  `O'Connor`, `Castellanos-Ruiz`, `A.` and `Nguyễn` stay exactly as written.
- **Source** is free text, not a fixed list.
- **Notes** are stored exactly as written, including line breaks.
- **Phone** is stored in E.164 format (`+17345550142`):
  - It may contain only digits, spaces, `(`, `)`, `-`, `.` and a leading `+`.
  - With a leading `+`, the digits are kept as the full international number.
  - Without a `+`, it must be exactly 10 digits and gets `+1`.
  - The result must have 8–15 digits. Anything else rejects the row.

## 8. Deduplication

This happens in memory, after validation and before anything is written. Rows that failed
validation never take part. Rows are checked in file order:

1. **Exact duplicates.** A row identical to an earlier row in every column (as written in
   the file) is folded into that row and counted as **merged**.
2. **Same email.** A later row with an email already seen is folded into the *first* row in
   the file with that email. The later row only fills fields that are blank on the first row
   and never overwrites a value. Its own `candidate_id` and other values are dropped.
   Counted as **merged**.
3. **Same candidate_id, different email.** The row is rejected. The reason names the row
   that already owns the ID.
4. **ID already in the database for a different email.** The row is rejected.
5. **Email already in the database.** The stored candidate is kept and only its blank
   fields are filled from the file. A stored value is never overwritten, including the
   stored `candidate_id`. Every such row is counted as **updated**, even when nothing was
   blank to fill. So every row lands in exactly one count:
   imported + merged + updated + rejected = rows in the file.

The import report is `{imported, merged, updated, rejected: [{row, reason}]}`.

## 9. Row numbers in the report

- Row numbers are what a spreadsheet shows: the header is row 1 and the first candidate is
  row 2.
- A quoted field spanning several lines (like C-1050's notes) is still one row and does not
  shift the count.

## 10. Bad files are rejected whole

Before any row is looked at, the whole upload is refused with HTTP 400 and one reason, and
nothing is written, if:
- it is not valid UTF-8 (a leading byte-order mark is allowed);
- it is empty, or has a header but no candidate rows;
- the header is not exactly the 12 expected columns (missing, extra, duplicated or
  misspelled; order doesn't matter);
- any row, including a blank line, has a different number of fields than the header.

## 11. All or nothing

- The whole file is written in one database transaction.
- Rejected rows don't stop the import; they are listed in the report. But a database error
  rolls back the entire file.

## 12. Who may import

- Only an admin may import (role-based access).
- No `X-Recruiter-Id` header returns 401. An unknown recruiter returns 403. A known recruiter
  who isn't an admin also returns 403.

## 13. Recruiters

- The roster is a fixed SQL seed matching recruiters.csv. A test checks they stay in sync.
- `role` is the source of truth for admin. The database enforces that a recruiter's regions
  contain `*` if and only if their role is `admin`.
- A recruiter's regions are stored as a JSON list of canonical region codes.

## Expected result for `candidates_import.csv`

The file has 53 candidate rows (spreadsheet rows 2–54).

**First import into an empty database:** imported 41, merged 3, updated 0, rejected 9.

| Row | ID | Outcome |
|---|---|---|
| 32 | C-1004 | merged: exact duplicate of row 5 |
| 33 | C-1031 | merged into row 2. C-1001 keeps its own ID and source (`LinkedIn`) |
| 34 | C-1032 | merged into row 17. Fills only C-1016's blank `notes` |
| 35 | C-1033 | rejected: invalid email `marcus.reed[at]gmail.com` |
| 36 | C-1034 | rejected: invalid email `tina.holloway.gmail.com` |
| 37 | C-1035 | rejected: email missing |
| 42 | C-1040 | rejected: `2026-02-30` is not a real date |
| 47 | C-1045 | rejected: unknown region `ZZ-99` |
| 49 | C-1047 | rejected: status `actve` (its `negotiable` salary alone would be fine) |
| 50 | C-1048 | rejected: status `on hold` |
| 53 | C-1010 | rejected: candidate_id C-1010 already belongs to row 11 |
| 54 | C-1051 | rejected: region missing |

**Stored candidates per region:**

| Region | Count |
|---|---|
| US-MW | 11 |
| US-NE | 8 |
| US-W | 8 |
| US-SE | 5 |
| PH-MNL | 5 |
| CO-BOG | 4 |

**Stored candidates per status:** active 30, interviewing 5, screening 5, withdrawn 1.

**What each recruiter sees:**

| Recruiter | Regions | Candidates |
|---|---|---|
| R-101 Dana | admin | 41 |
| R-102 Caleb | US-MW, US-NE | 19 |
| R-103 Marisol | PH-MNL, CO-BOG | 9 |
| R-104 Jordan | US-W, US-SE | 13 |
| R-105 Tessa | US-NE | 8 |

**Importing the same file again:** imported 0, merged 3, updated 41, rejected 9. The
database still holds 41 candidates.

**The two hostile rows are imported with their text unchanged:**
- C-1036, `last_name` = `O'Connor'); DROP TABLE candidates;--`
- C-1037, `notes` = `' OR '1'='1`

## Open questions (not decided yet; the code must not guess)

1. **Wording for a database ID clash.** For now the reason says only "already belongs to a
   different candidate". It doesn't reveal that candidate's email.
2. **Trimming candidate_id.** It's trimmed like the other required fields, so ` C-1010` and
   `C-1010` are the same ID. Confirm.
