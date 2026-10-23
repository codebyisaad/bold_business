# TechForce: candidate import and scoped recruiter view

This app imports a messy candidate CSV into PostgreSQL. Recruiters can then browse only the
candidates in their own regions. The stack is FastAPI with SQLAlchemy 2 and psycopg,
Postgres 16 with row-level security, and React with TypeScript, Tailwind and axios.

- **[BRIEF.md](BRIEF.md):** the product in plain English.
- **[DECISIONS.md](DECISIONS.md):** every data rule, with the expected numbers.
- **[NOTES.md](NOTES.md):** dedup and normalization decisions, the AI usage log, and what's next.
- **[postman/](postman/TechForce.postman_collection.json):** every endpoint, with tests. Run it with
  `npx newman run postman/TechForce.postman_collection.json --working-dir .` from the repo root.

## How I used AI, and where it fell short

I used Claude Code for this build from start to finish. It is fast and clean once it is
constrained, but three patterns needed correcting.

**1. It over-engineers by default.** For a two-table vertical slice it proposed Alembic,
async SQLAlchemy, a service layer and a generic repository. I cut them.
- The architecture should match the load we are actually targeting.
- A platform for thousands of candidates doesn't need to be built for a million users.
- Pretending otherwise costs infrastructure, onboarding time and review surface.

**2. It coerces where it should reject.** Unparseable salaries and dates were quietly turned
into null, but the brief says invalid rows are rejected with a reason.
- Every normalizer now either returns a canonical value or raises an error.
- The rules for missing versus invalid values are written down in DECISIONS.md.

**3. It leaves security gaps.** Without prompting, the first pass connected as the Docker
superuser, which silently bypasses row-level security, and it set the per-request recruiter
ID by formatting it into a `SET LOCAL` statement.
- The app now connects as a dedicated role that is not a superuser and owns no tables.
- The recruiter is set with a parameterized `select set_config(...)`.

## Run it

You need Docker, [uv](https://docs.astral.sh/uv/) and Node 20 or later.

```bash
cp .env.example .env && cp backend/.env.example backend/.env   # dev passwords; change them
docker compose up -d --wait            # Postgres 16 on localhost:5433
uv sync
uv run python -m app.db                # create the tables as the owner role
uv run python -m app.seed              # load recruiters.csv, then import candidates_import.csv
uv run uvicorn app.main:app --port 8000
npm --prefix frontend install && npm --prefix frontend run dev   # http://localhost:3000
uv run pytest                          # 162 tests against the real test database
```

## Data rules (summary; the full rules are in DECISIONS.md)

**Normalization**
- **Email:** trimmed, lowercased and validated. It is the candidate's identity.
- **Region:** uppercased and stripped of anything that isn't a letter or digit, then matched
  to the six canonical codes (`us-mw`, ` CO-BOG `, `USW` all resolve).
- **Status:** must be one of six fixed values, ignoring case.
- **Dates:** `YYYY-MM-DD`, `MM/DD/YYYY` or `DD-Mon-YYYY` are accepted and stored as ISO.
- **Salary:** `$`, commas and `k` are handled. Placeholders like `negotiable` become null.
- **Phones:** stored in E.164 format.
- **Bad values:** never silently nulled. The row is rejected with its spreadsheet row number
  and every reason.

**Dedup and merge** (done in memory, after validation, in file order)
1. An exact duplicate row is merged.
2. A later row with the same email is merged into the first one, and only fills that row's
   blank fields.
3. A reused `candidate_id` with a different email is rejected, and the reason names the row
   that owns the ID.
4. Re-importing a file only fills blanks on stored candidates. Stored values, including the
   ID, are never overwritten.

**Safety**
- Bad files are refused whole: over 10 MB, not UTF-8, or the wrong columns.
- The import is one transaction, written in batches of 500.
- All SQL is built with SQLAlchemy expressions, never by formatting strings.
- Only an admin may import.
- Candidate visibility is enforced in the query and again by Postgres row-level security. The
  app connects as a role that is not a superuser and owns nothing.
- A missing header gives 401 and an unknown recruiter gives 403.

**Result for the provided file:** 41 imported, 3 merged, 9 rejected. Recruiters see 19 (Caleb),
9 (Marisol), 13 (Jordan), 8 (Tessa), and the admin sees all 41.

## AI usage log

**Delegated to Claude Code**
- Scaffolding (uv, Docker, Vite).
- Drafting the SQL, normalizers, importer, writer, endpoints and React components.
- Writing the tests.
- Reading the CSV and listing every messy row.
- First drafts of these docs.

**Kept for myself**
- **Every data rule.** The AI listed the options; I chose each one, and the code may not
  guess a rule that isn't in DECISIONS.md.
- **Approving SQL.** Every schema change and query was proposed first and approved by me
  before it was written.
- **The security model:** role-based import, a header required even for the recruiter list,
  and row-level security as a second line of defence.
- **Commit structure and the final review of each diff.**

**Also caught during this build**
- The AI proposed leaving the recruiter list open with no header. I required a known
  recruiter, so the roster isn't exposed anonymously.
- The import endpoint first checked the upload against FastAPI's `UploadFile` class. That
  check never matches the object Starlette actually returns, so every upload got a 400. The
  real-database tests caught it before it was ever run by hand.
- Turning on row-level security made the seed script's import fail ("violates row-level
  security policy"). That was correct behaviour. The fix was to have the seed act as the
  roster's admin, not to weaken the policy.

## Next, with more time
- Stream large files instead of capping them at 10 MB (two passes over the spooled upload).
- Use a trigram index for search.
- Add browser tests for the page.
- Add a migrations tool instead of a single `schema.sql`.
