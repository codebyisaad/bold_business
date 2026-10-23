# Notes

The full rules, with the expected numbers for the provided file, are in
[DECISIONS.md](DECISIONS.md). This is the short version.

## Normalization

Every normalizer either returns a canonical value or rejects the row. Nothing invalid is
quietly turned into null. A blank optional field is stored as null; an invalid one rejects
the row, with its spreadsheet row number and every reason.

- **Email:** trimmed, lowercased and checked as a real address. It is the candidate's identity.
- **Region:** uppercased and stripped of anything but letters and digits, then matched to
  `US-MW, US-NE, US-SE, US-W, PH-MNL, CO-BOG`. So `us-mw`, ` CO-BOG ` and `USW` resolve,
  and `ZZ-99` is rejected.
- **Status:** one of `active, screening, interviewing, withdrawn, hired, rejected`, ignoring
  case. There is no spelling correction (`actve` and `on hold` are rejected).
- **Dates:** `YYYY-MM-DD`, `MM/DD/YYYY` and `DD-Mon-YYYY` are accepted, each with two-digit
  day and month, and stored as ISO. `2026-02-30` is rejected.
- **Salary:**
  - `$`, commas and spaces are stripped, and `k` means thousands.
  - Blank or `negotiable`/`na`/`n/a`/`tbd` becomes null.
  - Rounded half-up to two decimals.
  - Zero, negative or over 10,000,000 is rejected.
- **Phone:** stored in E.164 format; a plain 10-digit number gets `+1`.
- **Names, role and source:** whitespace is collapsed, case is never changed. Notes are
  stored exactly as written.

## Dedup and merge

This runs in memory after validation, in file order:

1. An exact duplicate row is **merged**.
2. A later row with the same email is **merged** into the first one. It only fills that
   row's blank fields, so Alicia keeps C-1001 and source LinkedIn.
3. The same `candidate_id` with a different email is **rejected**, and the reason names the
   row that owns it (Becca, row 53 → row 11).
4. Re-importing **updates** by email but only fills blanks. A stored value, including the ID,
   is never overwritten.

The database reports the inserted and updated counts. The whole file is one transaction,
written in batches of 500.

**Result for the provided file:** imported 41, merged 3, rejected 9. Importing it again gives
updated 41.

## AI usage log

**Delegated to Claude Code**
- Scaffolding.
- Drafting the SQL, normalizers, importer, writer, endpoints and React components.
- Writing the tests.
- Cataloguing every messy row in the CSV.
- First drafts of the docs.

**Kept for myself**
- **Every data rule.** The AI listed the options; I picked each one, and the code may not
  guess a rule that isn't in DECISIONS.md.
- **Approving all SQL** before it was written.
- **The security model.**
- **The commit structure and the review of each diff.**

**Caught and corrected**
- **An open recruiter list.** The AI proposed serving the recruiter list with no header. I
  required a known recruiter, so the roster isn't exposed anonymously.
- **A bad upload check.** The import endpoint checked the upload against FastAPI's
  `UploadFile`, which never matches the object Starlette returns, so every upload got a 400.
  The real-database tests caught it.
- **A blocked seed.** Turning on row-level security blocked the seed's import. The fix was to
  seed as the roster's admin, not to loosen the policy.
- **Recurring patterns** (detailed in the README): over-engineering for the load,
  coercing where it should reject, and security gaps around the database role.

## What I'd do next

- **Stream large uploads** (validate in one pass, write in a second) instead of capping them
  at 10 MB.
- **Add a trigram index** so search stays fast past a few thousand rows.
- **Add browser tests** for the recruiter switcher and the 401/403 states.
- **Use real authentication** instead of a trusted `X-Recruiter-Id` header.
- **Add a migrations tool** once the schema starts changing.
