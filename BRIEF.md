# What this product does

## The problem

A recruiting team keeps its candidates in an old system. When they export that list, it
comes out messy:
- The same person appears twice.
- Email addresses are typed in different ways.
- Dates are written in three different styles.
- Some salaries say "negotiable".
- A few entries are plainly wrong or even malicious.

The team also works by region. A recruiter covering the Midwest should only see Midwest
candidates, and should never see the people other recruiters are handling.

This product solves both problems. It cleans up the list as it is brought in, and it shows
each recruiter only the candidates they are responsible for.

## Bringing the list in

An administrator uploads the exported file. The product then goes through it line by line.

**Tidies up what it safely can**
- Capital letters and stray spaces in email addresses are ignored.
- A region written as "us-mw" or "USW" is recognised as the Midwest or the West.
- Dates written the American way, or with the month spelled out, are all converted to one
  standard style.
- "85k" is read as 85,000.
- Phone numbers are written in one consistent international format.

**Refuses what it can't trust.** It never guesses. If an email has no "@", a date doesn't
exist (such as the 30th of February), a region is unknown, or a status is misspelled, that
line is set aside. The administrator gets a report listing the line number and the exact
reason, so the problem can be fixed in the source.

**Recognises the same person**
- The email address identifies a person.
- If someone appears twice, they are kept once. The later copy may only fill in details
  that were missing, such as a note. It never replaces information already there.
- If two different people share the same ID number, the second one is set aside rather
  than mixed up with the first.

**Is safe to repeat.** Uploading the same file again doesn't create duplicates. Existing
people are recognised and left as they were, with only their missing details filled in.

**Is all or nothing.** If anything goes wrong partway through saving, nothing from that
upload is kept, so there's never a half-finished import.

**Has a size limit.** Files over 10 MB, or files that aren't a proper candidate list, are
turned away before anything is read.

**For the file we were given:** 41 people were brought in, 3 duplicates were combined, and
9 lines were set aside with reasons.

## Looking at candidates

Each recruiter opens a single page with:
- a table of candidates showing name, email, region, status, salary expectation and the
  date they applied;
- a search box for a name or an email;
- a filter for status (active, screening, interviewing and so on);
- pages of 25 at a time.

The page has a switcher to change which recruiter is viewing. Switching from Caleb, who
covers the Midwest and Northeast, to Marisol, who covers Manila and Bogotá, immediately
shows a different list. The administrator, Dana, sees everyone.

## Keeping it private

Who can see whom isn't left to the screen. It's enforced where the data is stored, twice
over:
- The question asked of the database only covers the recruiter's own regions.
- The database itself also refuses to hand over anyone outside those regions, even if
  someone wrote a careless question.

Someone who doesn't say who they are is turned away. So is someone who isn't on the team.
In neither case does the product fall back to showing everyone.

Only the administrator may bring in new lists.

## How we know it works

There are 162 automatic checks, run against a real database rather than a pretend one.
They cover:
- every messy line in the provided file and the exact reason it's set aside;
- the duplicate handling;
- the malicious entries, which are stored as harmless text;
- the all-or-nothing behaviour;
- what each recruiter can and cannot see.

## The choices we made, and what they cost

Every choice below solved the problem in front of us simply. Each one also gave something
up. For each, here's why we chose it, what it costs, what else we could have done, and how
it can grow.

### Refusing doubtful lines instead of guessing
- **Why:** a wrong guess is worse than a missing line. If "actve" were silently turned into
  "active", nobody would ever know the source was wrong.
- **Cost:** more lines are set aside, and someone has to fix them in the original system
  and upload again.
- **Other options:**
  - Auto-correct near-misses, so "actve" becomes "active".
  - Bring doubtful lines in but flag them for review.
- **Later:** a screen where the administrator sees the set-aside lines, corrects them on the
  spot, and sends them back in. This keeps the safety and removes the round trip.

### The email address decides who a person is
- **Why:** it's the one detail that is both present and unique for almost everyone.
- **Cost:**
  - A person who applies with two different emails becomes two people.
  - Two people sharing one email, such as a family address, would be treated as one.
- **Other options:** match on name and phone number together, or have a person confirm each
  suspected duplicate.
- **Later:** a "possible duplicates" list that suggests matches (same name and phone,
  different email) and lets a recruiter merge them by hand.

### The first copy of a person wins; later copies only fill gaps
- **Why:** nothing that is already known is ever lost or quietly replaced.
- **Cost:** newer information, such as an updated salary expectation in a later export,
  is ignored if an older value already exists.
- **Other options:** let the newest copy win, or ask the administrator line by line.
- **Later:** keep a history of every change, so newer values can be applied without losing
  the old ones, and anyone can see what changed and when.

### An upload is all or nothing
- **Why:** there's never a half-finished import that someone has to untangle.
- **Cost:** if something goes wrong near the end of a large file, the whole file must be sent
  again.
- **Other option:** save in sections and report which sections made it.
- **Later:** as files grow, run uploads in the background with a progress bar and an email
  when they're done, still keeping all or nothing.

### Uploads are capped at 10 MB and handled one at a time
- **Why:** it's simple and predictable. 10 MB is roughly 70,000 candidates, far more than a
  regional team exports at once. Handling uploads one at a time means two administrators
  can't create conflicting records.
- **Cost:**
  - A very large export has to be split into smaller files.
  - A second upload waits for the first to finish.
- **Other option:** read huge files a piece at a time, so size never matters.
- **Later:** switch to piece-by-piece reading once real files approach the limit. The rules
  wouldn't change, only how the file is read.

### Privacy is enforced where the data is stored, twice
- **Why:** a mistake in the screen, or in a future feature, still can't leak another
  region's candidates, because the storage itself refuses.
- **Cost:** a little more setup, and every new feature must respect the same rules.
- **Other option:** hide candidates only on the screen. That's simpler, but anyone who
  bypasses the screen sees everything.
- **Later:** the same approach scales naturally to more regions, more recruiters, or
  finer-grained rules (for example, by team or by role).

### Recruiters say who they are by picking from a list
- **Why:** the brief asked for a simple switcher so the effect of each recruiter's regions
  is easy to see.
- **Cost:** this is the biggest gap. Anyone who can reach the system can claim to be any
  recruiter, including the administrator.
- **Other option:** a real sign-in from day one.
- **Later:** this should be the first improvement before real use: sign in with company
  accounts, and the recruiter is known from the sign-in rather than chosen.

### Simple search, pages of 25, a fixed order
- **Why:** it's fast and easy to understand for thousands of candidates.
- **Cost:** search only finds exact fragments (a typo finds nothing), and it slows down
  once there are hundreds of thousands of candidates.
- **Other options:** a dedicated search service that tolerates typos, and sorting by any
  column.
- **Later:** add a search shortcut inside the database first, which is cheap and enough for
  a long time. Move to a dedicated search service only if typo-tolerant search becomes a
  real need.

### Checks run against a real database
- **Why:** the privacy rules live in the database, so only a real one proves they work.
- **Cost:** the checks need the database running and take slightly longer.
- **Other option:** a pretend database. It's faster, but it can't prove the privacy rules.

## How it grows

**Today: thousands of candidates, a handful of recruiters.**
What's built is enough. The one change to make before real use is a real sign-in.

**Tens of thousands of candidates, several teams.**
- A screen to review and fix set-aside lines.
- A "possible duplicates" list.
- A history of changes.
- The faster search shortcut.
- Uploads running in the background.

**Hundreds of thousands and beyond, many uploads a day.**
- Read large files piece by piece.
- A dedicated search service.
- Sorting and richer filters.
- Reporting on import quality over time, for example which sources produce the most
  rejected lines.

At each stage the rules in DECISIONS.md stay the same; only the machinery around them grows.
This is deliberate. We built for the load we have today, so the product stays easy to
understand, review and hand over, and each step up is added when it's actually needed.
