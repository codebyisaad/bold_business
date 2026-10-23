-- Applied by app.db.apply_schema() as techforce_owner. The rules behind each CHECK are in DECISIONS.md.

CREATE TABLE recruiters (
    recruiter_id     text PRIMARY KEY,
    full_name        text NOT NULL,
    email            text NOT NULL UNIQUE,
    role             text NOT NULL CHECK (role IN ('admin', 'recruiter')),
    assigned_regions jsonb NOT NULL CHECK (
        jsonb_typeof(assigned_regions) = 'array'
        AND jsonb_array_length(assigned_regions) > 0
        AND assigned_regions <@ '["*","US-MW","US-NE","US-SE","US-W","PH-MNL","CO-BOG"]'::jsonb),
    CHECK ((role = 'admin') = (assigned_regions ? '*'))
);

CREATE TABLE candidates (
    candidate_id       text PRIMARY KEY CHECK (btrim(candidate_id) <> ''),
    first_name         text NOT NULL CHECK (btrim(first_name) <> ''),
    last_name          text NOT NULL CHECK (btrim(last_name) <> ''),
    email              text NOT NULL UNIQUE CHECK (email = lower(btrim(email))),
    phone              text CHECK (phone ~ '^\+[0-9]{8,15}$'),
    region_code        text NOT NULL CHECK (region_code IN ('US-MW','US-NE','US-SE','US-W','PH-MNL','CO-BOG')),
    desired_role       text,
    salary_expectation numeric(12,2) CHECK (salary_expectation > 0 AND salary_expectation <= 10000000),
    applied_date       date,
    status             text NOT NULL CHECK (status IN ('active','screening','interviewing','withdrawn','hired','rejected')),
    source             text,
    notes              text
);

CREATE INDEX candidates_region_code_idx ON candidates (region_code);

GRANT SELECT ON recruiters TO techforce_app;
GRANT SELECT, INSERT, UPDATE ON candidates TO techforce_app;

-- Row-level security (DECISIONS.md 12 and 14). The API sets app.recruiter_id for each
-- transaction with set_config(..., true). When it isn't set, current_setting(..., true) is
-- NULL or '' and matches no recruiter, so every policy denies. The owner is not subject to
-- these policies; the app role always is.
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

CREATE POLICY candidates_read ON candidates FOR SELECT TO techforce_app
USING (EXISTS (
    SELECT 1 FROM recruiters r
    WHERE r.recruiter_id = current_setting('app.recruiter_id', true)
      AND (r.role = 'admin' OR r.assigned_regions ? candidates.region_code)));

CREATE POLICY candidates_insert ON candidates FOR INSERT TO techforce_app
WITH CHECK (EXISTS (
    SELECT 1 FROM recruiters r
    WHERE r.recruiter_id = current_setting('app.recruiter_id', true) AND r.role = 'admin'));

CREATE POLICY candidates_update ON candidates FOR UPDATE TO techforce_app
USING (EXISTS (
    SELECT 1 FROM recruiters r
    WHERE r.recruiter_id = current_setting('app.recruiter_id', true) AND r.role = 'admin'))
WITH CHECK (EXISTS (
    SELECT 1 FROM recruiters r
    WHERE r.recruiter_id = current_setting('app.recruiter_id', true) AND r.role = 'admin'));
