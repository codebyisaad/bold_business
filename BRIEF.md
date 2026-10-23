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
