# Test report

Generated from an actual run of every suite in this repo. Re-run with the commands at the bottom.

| | |
|---|---|
| Run | 2026-10-23 19:22 PKT |
| Commit | 71414cf |
| Python | 3.12.12 |
| pytest | 9.1.1 |
| PostgreSQL | 16.15 (Docker postgres:16) |
| Node | v26.6.0 |

## Summary

| Suite | Runs against | Result |
|---|---|---|
| Backend: pytest (5 files) | Pure code + real Postgres 16 test database | **162/162 passed** in 1.05s |
| API: Postman collection (newman) | Live backend on :8000, seeded app database | **19/19 requests, 42/42 assertions passed** |
| Frontend: type-check + build (`tsc -b && vite build`) | `frontend/src` | **passed (exit 0)** |
| Frontend: lint (oxlint) | `frontend/src` | **passed, no findings** |

No test touches a mocked database. The DB tests connect as the app role (`techforce_app`), exactly like the API; the schema is applied once per run and the candidates table is emptied before each test.

## Brief requirements → evidence

| Requirement (brief) | Proven by |
|---|---|
| Import endpoint returns `{imported, merged, rejected:[{row, reason}]}` | test_import_api: first import; Postman: Import CSV (as admin) |
| Pydantic v2 validation; invalid rows rejected, not dropped | test_importer: first import rejected rows and reasons, several problems, missing required fields |
| Normalize emails, regions, statuses, dates, salary | test_normalize (all 78 cases); test_import_api: normalized values are stored |
| Dedup: exact duplicate, same email, candidate_id collision | test_importer: merged rows, Alicia keeps id and source, Amara fills blanks, id collision |
| SQL injection impossible | test_importer + test_import_api: hostile rows stored verbatim and the table survives |
| Batched writes, no row-at-a-time | test_import_api: writes are batched (41 rows → 5 INSERTs at batch size 10) |
| Scope enforced in the data layer (RLS a plus) | test_read_api: RLS returns nothing with no recruiter set; RLS alone scopes an unfiltered query |
| Recruiter sees only their regions; admin sees all | test_read_api: each recruiter sees their regions (41/19/9/13/8); Postman: per-recruiter lists |
| Unknown recruiter → 403, not empty 200 | test_read_api + test_import_api + Postman: 401 without header, 403 unknown |
| Recruiter cannot retrieve out-of-region candidate; admin can | test_read_api: recruiter cannot retrieve a candidate outside their regions |
| Search, status filter, pagination | test_read_api: search, status, paging tests; Postman: search, filter, page 2 |
| Unicode names | test_importer + test_import_api: unicode round-trip; Postman: Unicode name |

## Backend tests by file

| File | Kind | Covers | Result |
|---|---|---|---|
| `test_database.py` | Real Postgres | App role is not superuser, owns nothing, cannot DELETE; recruiter seed matches CSV; recruiter CHECKs | 9/9 ✅ |
| `test_import_api.py` | Real Postgres | POST /import end to end: report, stored values, re-import fill-blanks, batching, rollback, admin-only, size/bad-file limits | 17/17 ✅ |
| `test_importer.py` | Pure, no DB | Parse + plan against the real CSV: counts, exact rejected rows and reasons, merges, dedup, bad files (8–10) | 28/28 ✅ |
| `test_normalize.py` | Pure, no DB | Each field rule: email, region, status, date, salary, phone, text (DECISIONS.md 2–7) | 78/78 ✅ |
| `test_read_api.py` | Real Postgres | GET /candidates and /recruiters: per-recruiter scope, RLS without WHERE, search, status, paging, 401/403 | 30/30 ✅ |

<details><summary><code>test_database.py</code>: 9 tests</summary>

| Test | Result |
|---|---|
| app role is not superuser and cannot bypass rls | ✅ pass |
| app role owns no table | ✅ pass |
| app role cannot delete candidates | ✅ pass |
| app role cannot write recruiters | ✅ pass |
| seeded recruiters match the csv | ✅ pass |
| recruiter constraints `[admin-regions0]` | ✅ pass |
| recruiter constraints `[recruiter-regions1]` | ✅ pass |
| recruiter constraints `[recruiter-regions2]` | ✅ pass |
| recruiter constraints `[recruiter-regions3]` | ✅ pass |

</details>

<details><summary><code>test_import_api.py</code>: 17 tests</summary>

| Test | Result |
|---|---|
| first import | ✅ pass |
| stored counts per region and status | ✅ pass |
| reimport counts every stored candidate as updated | ✅ pass |
| reimport only fills blanks and keeps the stored id | ✅ pass |
| normalized values are stored | ✅ pass |
| hostile rows are stored verbatim and the table survives | ✅ pass |
| unicode and multiline values round trip | ✅ pass |
| writes are batched | ✅ pass |
| a database error rolls back the whole file | ✅ pass |
| only an admin can import `[headers0-401]` | ✅ pass |
| only an admin can import `[headers1-401]` | ✅ pass |
| only an admin can import `[headers2-403]` | ✅ pass |
| only an admin can import `[headers3-403]` | ✅ pass |
| declared size over the limit is refused before reading | ✅ pass |
| file size over the limit is refused | ✅ pass |
| bad file is refused whole | ✅ pass |
| missing file field is refused | ✅ pass |

</details>

<details><summary><code>test_importer.py</code>: 28 tests</summary>

| Test | Result |
|---|---|
| file has 53 candidate rows numbered like a spreadsheet | ✅ pass |
| first import counts | ✅ pass |
| first import rejected rows and reasons | ✅ pass |
| merged rows point at the row they fold into | ✅ pass |
| alicia keeps her original id and source | ✅ pass |
| amara only gets her blank notes filled | ✅ pass |
| exact duplicate is stored once | ✅ pass |
| id collision keeps the first owner | ✅ pass |
| counts per region | ✅ pass |
| counts per status | ✅ pass |
| messy values are normalized | ✅ pass |
| hostile rows are kept as literal text | ✅ pass |
| unicode and multiline values survive | ✅ pass |
| reimport updates every stored candidate | ✅ pass |
| stored id owned by another email rejects the row | ✅ pass |
| same email stored under another id is an update | ✅ pass |
| row with several problems lists every reason | ✅ pass |
| every missing required field is named | ✅ pass |
| blank optional fields are null | ✅ pass |
| bad file is rejected whole `[-file is empty]` | ✅ pass |
| bad file is rejected whole `[\xff\xfe\x00-file is not valid UTF-8]` | ✅ pass |
| bad file is rejected whole `[candidate_id,first_name,last_name,email,phone,region_code,desired_role,salary_expectation,applied_date,status,source,notes\r\n-file has a header but no candidate rows]` | ✅ pass |
| bad file is rejected whole `[candidate_id,first_name,last_name,email,phone,region_code,desired_role,salary_expectation,applied_date,status,source\r\nC-9001,Test,Person,test.person@gmail.com,,US-MW,,,,Active,\r\n-missing notes]` | ✅ pass |
| bad file is rejected whole `[candidate_id,first_name,last_name,email,phone,region_code,desired_role,salary_expectation,applied_date,status,source,notes,extra\r\nC-9001,Test,Person,test.person@gmail.com,,US-MW,,,,Active,,,\r\n-unexpected extra]` | ✅ pass |
| bad file is rejected whole `[candidate_id,first_name,last_name,email,phone,region_code,desired_role,salary_expectation,applied_date,status,source,email\r\nC-9001,Test,Person,test.person@gmail.com,,US-MW,,,,Active,,test.person@gmail.com\r\n-duplicated email]` | ✅ pass |
| bad file is rejected whole `[candidate_id,first_name,last_name,email,phone,region_code,desired_role,salary_expectation,applied_date,status,source,notes\r\nC-9001,Test,Person,test.person@gmail.com,,US-MW,,,,Active,,\r\nC-9002,Only,Three\r\n-row 3 has 3 fields, expected 12]` | ✅ pass |
| bad file is rejected whole `[candidate_id,first_name,last_name,email,phone,region_code,desired_role,salary_expectation,applied_date,status,source,notes\r\nC-9001,Test,Person,test.person@gmail.com,,US-MW,,,,Active,,\r\n\r\n-row 3 has 0 fields, expected 12]` | ✅ pass |
| byte order mark is allowed | ✅ pass |

</details>

<details><summary><code>test_normalize.py</code>: 78 tests</summary>

| Test | Result |
|---|---|
| email is trimmed and lowercased `[  Alicia.Trent@Gmail.com -alicia.trent@gmail.com]` | ✅ pass |
| email is trimmed and lowercased `[m.bellamy@outlook.com-m.bellamy@outlook.com]` | ✅ pass |
| invalid email is rejected `[marcus.reed[at]gmail.com]` | ✅ pass |
| invalid email is rejected `[tina.holloway.gmail.com]` | ✅ pass |
| invalid email is rejected `[a@b]` | ✅ pass |
| invalid email is rejected `[a b@gmail.com]` | ✅ pass |
| region resolves to canonical code `[US-MW-US-MW]` | ✅ pass |
| region resolves to canonical code `[us-mw-US-MW]` | ✅ pass |
| region resolves to canonical code `[ CO-BOG -CO-BOG]` | ✅ pass |
| region resolves to canonical code `[USW-US-W]` | ✅ pass |
| region resolves to canonical code `[ph mnl-PH-MNL]` | ✅ pass |
| unknown region is rejected `[ZZ-99]` | ✅ pass |
| unknown region is rejected `[US]` | ✅ pass |
| unknown region is rejected `[US-MWX]` | ✅ pass |
| unknown region is rejected `[USMW1]` | ✅ pass |
| status ignores case and surrounding spaces `[Active-active]` | ✅ pass |
| status ignores case and surrounding spaces `[ACTIVE-active]` | ✅ pass |
| status ignores case and surrounding spaces `[ Interviewing -interviewing]` | ✅ pass |
| status ignores case and surrounding spaces `[hired-hired]` | ✅ pass |
| status ignores case and surrounding spaces `[Rejected-rejected]` | ✅ pass |
| status outside the enum is rejected `[actve]` | ✅ pass |
| status outside the enum is rejected `[on hold]` | ✅ pass |
| status outside the enum is rejected `[on-hold]` | ✅ pass |
| status outside the enum is rejected `[act ive]` | ✅ pass |
| accepted date formats convert to a date `[2026-05-14-expected0]` | ✅ pass |
| accepted date formats convert to a date `[06/30/2026-expected1]` | ✅ pass |
| accepted date formats convert to a date `[14-May-2026-expected2]` | ✅ pass |
| accepted date formats convert to a date `[14-may-2026-expected3]` | ✅ pass |
| accepted date formats convert to a date `[-None]` | ✅ pass |
| accepted date formats convert to a date `[   -None]` | ✅ pass |
| invalid date is rejected `[2026-02-30-is not a real calendar date]` | ✅ pass |
| invalid date is rejected `[02/30/2026-is not a real calendar date]` | ✅ pass |
| invalid date is rejected `[6/30/2026-is not YYYY-MM-DD]` | ✅ pass |
| invalid date is rejected `[2026-5-14-is not YYYY-MM-DD]` | ✅ pass |
| invalid date is rejected `[2026/05/14-is not YYYY-MM-DD]` | ✅ pass |
| invalid date is rejected `[14-Mai-2026-is not YYYY-MM-DD]` | ✅ pass |
| invalid date is rejected `[yesterday-is not YYYY-MM-DD]` | ✅ pass |
| salary parses to two decimals `[88000-expected0]` | ✅ pass |
| salary parses to two decimals `[$95,000-expected1]` | ✅ pass |
| salary parses to two decimals `[97,500-expected2]` | ✅ pass |
| salary parses to two decimals `[85k-expected3]` | ✅ pass |
| salary parses to two decimals `[85.5K-expected4]` | ✅ pass |
| salary parses to two decimals `[$ 1 000-expected5]` | ✅ pass |
| salary parses to two decimals `[95000.005-expected6]` | ✅ pass |
| salary parses to two decimals `[95000.004-expected7]` | ✅ pass |
| salary parses to two decimals `[10000000-expected8]` | ✅ pass |
| blank or placeholder salary is null `[]` | ✅ pass |
| blank or placeholder salary is null `[  ]` | ✅ pass |
| blank or placeholder salary is null `[negotiable]` | ✅ pass |
| blank or placeholder salary is null `[Negotiable]` | ✅ pass |
| blank or placeholder salary is null `[NA]` | ✅ pass |
| blank or placeholder salary is null `[n/a]` | ✅ pass |
| blank or placeholder salary is null `[N/A]` | ✅ pass |
| blank or placeholder salary is null `[tbd]` | ✅ pass |
| blank or placeholder salary is null `[TBD]` | ✅ pass |
| invalid salary is rejected `[0-must be greater than zero]` | ✅ pass |
| invalid salary is rejected `[0.004-must be greater than zero]` | ✅ pass |
| invalid salary is rejected `[-5-must be greater than zero]` | ✅ pass |
| invalid salary is rejected `[10000000.01-is above 10,000,000]` | ✅ pass |
| invalid salary is rejected `[10001k-is above 10,000,000]` | ✅ pass |
| invalid salary is rejected `[abc-is not a number]` | ✅ pass |
| invalid salary is rejected `[1e5-is not a number]` | ✅ pass |
| invalid salary is rejected `[unknown-is not a number]` | ✅ pass |
| phone is normalized to e164 `[+1 (734) 555-0142-+17345550142]` | ✅ pass |
| phone is normalized to e164 `[734-555-0187-+17345550187]` | ✅ pass |
| phone is normalized to e164 `[(312) 555-0165-+13125550165]` | ✅ pass |
| phone is normalized to e164 `[616.555.0134-+16165550134]` | ✅ pass |
| phone is normalized to e164 `[+57 601 555 0177-+576015550177]` | ✅ pass |
| phone is normalized to e164 `[+63 917 555 0122-+639175550122]` | ✅ pass |
| phone is normalized to e164 `[-None]` | ✅ pass |
| invalid phone is rejected `[555-0142-needs a \\+country code or exactly 10 digits]` | ✅ pass |
| invalid phone is rejected `[1-734-555-0142-needs a \\+country code or exactly 10 digits]` | ✅ pass |
| invalid phone is rejected `[+1 734 555 0142 ext 5-contains characters other than]` | ✅ pass |
| invalid phone is rejected `[+12345-must have 8 to 15 digits]` | ✅ pass |
| collapse trims without changing case `[  Full-Stack   Engineer -Full-Stack Engineer]` | ✅ pass |
| collapse trims without changing case `[O'Connor-O'Connor]` | ✅ pass |
| collapse trims without changing case `[Nguy\u1ec5n-Nguy\u1ec5n]` | ✅ pass |
| collapse trims without changing case `[   -None]` | ✅ pass |

</details>

<details><summary><code>test_read_api.py</code>: 30 tests</summary>

| Test | Result |
|---|---|
| each recruiter sees their regions `[R-101-41]` | ✅ pass |
| each recruiter sees their regions `[R-102-19]` | ✅ pass |
| each recruiter sees their regions `[R-103-9]` | ✅ pass |
| each recruiter sees their regions `[R-104-13]` | ✅ pass |
| each recruiter sees their regions `[R-105-8]` | ✅ pass |
| items are only from the recruiters regions | ✅ pass |
| recruiter cannot retrieve a candidate outside their regions | ✅ pass |
| missing or unknown recruiter never falls back `[headers0-401]` | ✅ pass |
| missing or unknown recruiter never falls back `[headers1-403]` | ✅ pass |
| rls returns nothing when no recruiter is set | ✅ pass |
| rls alone scopes an unfiltered query `[R-101-41]` | ✅ pass |
| rls alone scopes an unfiltered query `[R-103-9]` | ✅ pass |
| rls alone scopes an unfiltered query `[R-999-0]` | ✅ pass |
| search matches full name or email `[Alicia Trent-expected0]` | ✅ pass |
| search matches full name or email `[alicia trent-expected1]` | ✅ pass |
| search matches full name or email `[TRENT-expected2]` | ✅ pass |
| search matches full name or email `[hweiss@protonmail-expected3]` | ✅ pass |
| search matches full name or email `[Nguy\u1ec5n-expected4]` | ✅ pass |
| search matches full name or email `[%-expected5]` | ✅ pass |
| search matches full name or email `[_-expected6]` | ✅ pass |
| search never widens the scope | ✅ pass |
| status filter narrows within scope | ✅ pass |
| unknown status is 422 | ✅ pass |
| pages are 25 by default ordered by id | ✅ pass |
| page past the end is empty | ✅ pass |
| invalid paging is 422 `[params0]` | ✅ pass |
| invalid paging is 422 `[params1]` | ✅ pass |
| invalid paging is 422 `[params2]` | ✅ pass |
| candidate shape uses iso dates and decimal strings | ✅ pass |
| recruiter list has everyone without emails | ✅ pass |

</details>

## API collection (Postman / newman)

| Request | Status | Assertions |
|---|---|---|
| List recruiters (as admin) | 200 | 3/3 ✅ |
| List recruiters (no header → 401) | 401 | 1/1 ✅ |
| List recruiters (unknown → 403) | 403 | 1/1 ✅ |
| Import CSV (as admin) | 200 | 5/5 ✅ |
| Import CSV (recruiter, not admin → 403) | 403 | 1/1 ✅ |
| Import CSV (no header → 401) | 401 | 1/1 ✅ |
| List candidates (admin sees all) | 200 | 3/3 ✅ |
| List candidates (Caleb: US-MW, US-NE) | 200 | 3/3 ✅ |
| List candidates (Marisol: PH-MNL, CO-BOG) | 200 | 3/3 ✅ |
| List candidates (Jordan: US-W, US-SE) | 200 | 3/3 ✅ |
| List candidates (Tessa: US-NE) | 200 | 3/3 ✅ |
| Search full name (admin finds Alicia) | 200 | 3/3 ✅ |
| Search out of region (Marisol cannot see Alicia) | 200 | 2/2 ✅ |
| Filter by status | 200 | 3/3 ✅ |
| Page 2 | 200 | 2/2 ✅ |
| Unicode name | 200 | 2/2 ✅ |
| Invalid status → 422 | 422 | 1/1 ✅ |
| No header → 401 | 401 | 1/1 ✅ |
| Unknown recruiter → 403 | 403 | 1/1 ✅ |

## Not covered by automated tests

- **Visual rendering in a browser.** There are no browser tests yet. The frontend is type-checked, built and linted, and its API layer and components were exercised once by hand against the live API (header switching, 401/403 messages, Unicode names), but that check is not part of this suite.
- **Two concurrent imports.** The advisory lock that serializes imports is in place but not exercised by a test.
- **Setup from a clean machine.** The README steps were not re-run from an empty Docker volume for this report.

## How to re-run

```bash
docker compose up -d --wait
uv run pytest                              # backend: sets up the test DB itself
uv run python -m app.db && uv run python -m app.seed   # app DB for the API collection
uv run uvicorn app.main:app --port 8000     # in another terminal
npx newman run postman/TechForce.postman_collection.json --working-dir .
npm --prefix frontend run build && npm --prefix frontend run lint
```
