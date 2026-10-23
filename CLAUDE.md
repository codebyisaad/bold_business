# CLAUDE.md

## Stack
- Python 3.12, managed with uv (`uv run ...`, `uv add ...`); never pip directly.
- FastAPI, SQLAlchemy 2 (sync) + psycopg, Pydantic for validation, pydantic-settings for config.
- PostgreSQL 16, running as a standalone container service.
- Tests: pytest + httpx against a real Postgres test database.

## Layout
```
backend/app/main.py            FastAPI app wiring
backend/app/config.py          pydantic-settings: DATABASE_URL, TEST_DATABASE_URL (from backend/.env)
backend/app/models.py          SQLAlchemy models
backend/app/domain/            pure logic, no I/O
  normalize.py, schemas.py, importer.py
backend/app/auth.py            recruiter identification
backend/app/repositories/candidates.py
backend/app/routers/
backend/tests/
frontend/
DECISIONS.md                   every data rule, in plain English
```

## Hard rules (graded)
1. SQL only via SQLAlchemy expressions / bound parameters. No f-strings, `.format()` or `%`
   in any SQL, including session settings: use `select(func.set_config(...))`,
   never `SET LOCAL` with a literal.
2. Writes are batched (one multi-row insert/update), never row-by-row in a loop.
3. Bad data is rejected with its row number and reason. Never silently coerced to NULL.
4. Candidate visibility is enforced in the database: filtered in the query itself and
   backed by Postgres row-level security, with the app connecting as a non-superuser role.
   No filtering in Python after the fact.
5. Missing recruiter header -> 401. Unknown recruiter -> 403. Never fall back to showing everything.
6. Every behaviour has a test against the real test database. No mocked DB.

## How to work
- Before writing anything that contains SQL (models, migrations, RLS policies, repository
  queries), propose the file first and wait for my approval. Then implement, so I can read the diff.
- If a data rule is not in DECISIONS.md, ask me. Do not guess or assume.
- Once I approve a data rule, record it in DECISIONS.md.
- No layers or abstractions we don't need yet.

## Commands
- Install deps: `uv sync`
- Database: `docker compose up -d --wait` (host port 5433), then `uv run python -m app.db` (add `--reset` to drop tables first) and `uv run python -m app.seed` (loads both CSVs). Tests set up the test DB themselves.
- Run API: `uv run fastapi dev backend/app/main.py`
- Tests: `uv run pytest backend/tests`
