#!/bin/bash
# Runs once, on an empty data volume. Creates the two roles and the two databases.
# Tables are created later by `python -m app.db` connecting as techforce_owner.
#   techforce_owner: owns the databases and tables. Not a superuser.
#   techforce_app:   what the API connects as. Owns nothing, gets grants only.
set -euo pipefail

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres \
  -v owner_password="$OWNER_DB_PASSWORD" \
  -v app_password="$APP_DB_PASSWORD" <<'SQL'
CREATE ROLE techforce_owner LOGIN PASSWORD :'owner_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE techforce_app LOGIN PASSWORD :'app_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE DATABASE techforce OWNER techforce_owner;
CREATE DATABASE techforce_test OWNER techforce_owner;
SQL
