# Plan: TechForce candidate import and scoped recruiter view

Status: planning only. Nothing is implemented yet.

The data rules live in **DECISIONS.md** and are the source of truth. This plan only points
at them. Anything still undecided is listed in section 5 or in DECISIONS.md's open questions,
and must be answered before the code that depends on it is written.

## 1. What is being asked (from the brief)

| Part | Deliverable | Graded on |
|---|---|---|
| 1 | `POST /api/v1/candidates/import` (CSV upload into Postgres) | Pydantic v2 validation, normalization, explicit dedup rules, no SQL injection, batched writes |
| 2 | `GET /api/v1/candidates?search=&status=` with pagination | `X-Recruiter-Id` header; scope enforced in the data layer (RLS is a bonus); unknown recruiter gives 403 |
| 3 | React + TypeScript single page | Table (name, email, region, role, status, applied date), search, status filter, a switcher for the 5 recruiters, Unicode renders correctly |
| 4 | pytest | Dedup, invalid email, injection rows, recruiter cannot see an out-of-region candidate, admin can. Run on camera |
| 5 | NOTES.md | Dedup and normalization rules, AI usage log (including one AI mistake you caught), what you'd do next |
| Also | README.md, docker-compose.yml, meaningful commit history, screen recording (3 hours max) | |

**Deliberate differences from the brief (documented in DECISIONS.md):**
- The import report adds an `updated` count: `{imported, merged, updated, rejected: [{row, reason}]}`.
- A missing `X-Recruiter-Id` header returns 401. The brief only specifies 403 for an unknown
  recruiter.

## 2. The input files

**candidates_import.csv**
- UTF-8, no BOM, NFC. CRLF line endings.
- 53 candidate rows: spreadsheet rows 2–54, with the header as row 1.
- C-1050's notes field (row 51) spans three physical lines but is one row.

**recruiters.csv**
- 5 recruiters. `assigned_regions` is pipe-delimited; `*` means admin.

| Recruiter | Name | Regions |
|---|---|---|
| R-101 | Dana Whitmore | `*` (admin) |
| R-102 | Caleb Nguyen | US-MW, US-NE |
| R-103 | Marisol Vega | PH-MNL, CO-BOG |
| R-104 | Jordan Blake | US-W, US-SE |
| R-105 | Tessa Iqbal | US-NE (overlaps Caleb) |

## 3. What's messy, and how the rules handle it

Row numbers are spreadsheet rows (header = row 1). The rule numbers refer to DECISIONS.md
sections.

| Row | ID | Problem | Outcome |
|---|---|---|---|
| 32 | C-1004 | Exact copy of row 5 | merged (7.1) |
| 33 | C-1031 | Email `  Alicia.Trent@Gmail.com ` = C-1001 (row 2) | merged into C-1001; ID C-1031 dropped (7.2) |
| 34 | C-1032 | Email = C-1016 Amara (row 17); different name, phone, salary, date | merged; fills only C-1016's blank `notes` (7.2) |
| 53 | C-1010 | Becca Storm reuses Sofía's ID (row 11) with a different email | rejected, names row 11 (7.3) |
| 35 | C-1033 | `marcus.reed[at]gmail.com` | rejected (2) |
| 36 | C-1034 | `tina.holloway.gmail.com` | rejected (2) |
| 37 | C-1035 | Email empty | rejected (1) |
| 38 | C-1036 | `last_name` = `O'Connor'); DROP TABLE candidates;--` | imported unchanged; bound parameters only |
| 39 | C-1037 | `notes` = `' OR '1'='1` | imported unchanged |
| 40 | C-1038 | `06/30/2026` | imported as `2026-06-30` (5) |
| 41 | C-1039 | `14-May-2026` | imported as `2026-05-14` (5) |
| 42 | C-1040 | `2026-02-30` | rejected (5) |
| 43 | C-1041 | Date blank | imported, date null (5) |
| 44 | C-1042 | `us-mw` | `US-MW` (3) |
| 45 | C-1043 | ` CO-BOG ` | `CO-BOG` (3) |
| 46 | C-1044 | `USW` | `US-W` (3) |
| 47 | C-1045 | `ZZ-99` | rejected (3) |
| 54 | C-1051 | Region blank | rejected (1) |
| 48 | C-1046 | `ACTIVE`, salary `85k` | imported: `active`, 85000.00 (4, 6) |
| 49 | C-1047 | `actve`, salary `negotiable` | rejected for status; the salary alone would be null (4, 6) |
| 50 | C-1048 | `on hold`, salary blank | rejected for status (4) |

**Other things to handle**
- Salary formats: `$95,000`, `97,500` and `88000` all parse (6).
- Unicode names: rows 7, 9, 16, 45, 46. Row 9 puts the Vietnamese family name in
  `first_name`. Store it as given.
- Phones come in every format. Their handling is open (DECISIONS open question 9).
- Several notes are the test author's hints ("Which record wins?"). They are data and
  are stored as-is.

## 4. Expected numbers (the tests will assert these)

Produced by `scratchpad/expected_report.py`, a throwaway, stdlib-only script that applies
the rules to the real CSV.

**First import:** imported 41, merged 3, updated 0, rejected 9.

| | Breakdown |
|---|---|
| Per region | US-MW 11, US-NE 8, US-W 8, US-SE 5, PH-MNL 5, CO-BOG 4 |
| Per status | active 30, interviewing 5, screening 5, withdrawn 1 |
| Visible per recruiter | Dana 41, Caleb 19, Marisol 9, Jordan 13, Tessa 8 |

**Same file again:** imported 0, merged 3, updated 41, rejected 9. Still 41 candidates.

The full per-row list is in DECISIONS.md.

## 5. Decisions still needed (not about the data)

1. **Import authorization:** (a) admin only, via an RLS policy that lets admins write;
   (b) an open endpoint using a separate import DB role.
2. **RLS mechanics:**
   - Fixed by your rules: the app connects as a non-superuser role without `BYPASSRLS`, and
     each request runs `select set_config('app.recruiter_id', :id, true)`. An unset setting
     must match no rows.
   - Options: (a) the policy joins a `recruiter_regions` table; (b) regions are stored as a
     `text[]` on `recruiters`.
3. **Admin source of truth:** (a) `assigned_regions = *`, as the brief says; (b) the `role`
   column.
4. **"Cannot retrieve a candidate" test:** (a) add `GET /candidates/{id}`, returning 404 when
   out of scope; (b) assert through the list endpoint only.
5. **Recruiter list for the switcher:** (a) `GET /api/v1/recruiters`; (b) hardcoded in the
   frontend.
6. **Pagination and search:**
   - (a) `limit` and `offset` returning `{items, total}`; (b) `page` and `page_size`.
   - Which fields `search` matches.
7. **Recruiter seeding:** (a) load recruiters.csv during DB setup; (b) a fixed SQL seed.
8. **NOTES.md vs DECISIONS.md:** the brief grades NOTES.md. (a) NOTES.md summarizes and links
   to DECISIONS.md; (b) merge them.
9. **Repo hygiene:**
   - Python 3.14 → 3.12.
   - Remove the leftover `src/`.
   - Keep the brief PDFs out of git.
   - Add docker-compose.yml.
   - Make the first commit.

## 6. Build order (each step: propose SQL and schema, get approval, implement, test against the real DB)

1. Repo hygiene (5.9).
2. `domain/normalize.py` and `domain/schemas.py`: pure functions, a unit test per rule and
   per row in section 3.
3. `domain/importer.py`: validate, then dedup in memory, producing the report. Tests assert
   the section 4 numbers without a DB.
4. Schema, app role and RLS policies (proposed first).
5. `repositories/candidates.py`: one transaction, batched upsert by email, the DB-side ID
   check. Then `POST /import`, with real-DB tests for both imports in section 4 and a
   rollback test.
6. `auth.py` (401/403) and the scoped `GET /candidates`, plus per-recruiter count tests from
   section 4.
7. Frontend: table, search, status filter, recruiter switcher.
8. README, NOTES.md, and a full test run on camera.
