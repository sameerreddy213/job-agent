-- ============================================================
-- job-agent — Phase 0 database bootstrap
-- The POSTGRES_DB/USER are created by the official image from env vars.
-- This script only enables extensions and a schema namespace.
-- Full table schema (profile, resumes, resume_versions, sources, jobs,
-- job_scores, materials, applications, run_health, audit_log, users,
-- analytics) is added via migrations in Phase 1.
-- ============================================================

-- UUID + crypto helpers
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Case-insensitive text (useful for emails/usernames/dedupe)
CREATE EXTENSION IF NOT EXISTS "citext";

-- Trigram search (company/title search in dashboard)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Application schema namespace
CREATE SCHEMA IF NOT EXISTS app;

-- Sanity marker so we can confirm init ran
CREATE TABLE IF NOT EXISTS app._bootstrap (
    id          INT PRIMARY KEY DEFAULT 1,
    initialized BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT single_row CHECK (id = 1)
);

INSERT INTO app._bootstrap (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;
