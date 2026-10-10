CREATE TABLE model_budget_buckets (
    budget_scope TEXT NOT NULL,
    budget_key TEXT NOT NULL,
    cap_usd NUMERIC NOT NULL CHECK (cap_usd > 0 AND cap_usd <= 25),
    reserved_usd NUMERIC NOT NULL DEFAULT 0 CHECK (reserved_usd >= 0 AND reserved_usd <= cap_usd),
    PRIMARY KEY (budget_scope, budget_key)
);

CREATE TABLE model_jobs (
    job_id TEXT PRIMARY KEY CHECK (job_id ~ '^[0-9a-f]{32}$'),
    idempotency_key TEXT NOT NULL UNIQUE,
    fingerprint TEXT NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    spec TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    budget_scope TEXT NOT NULL,
    budget_key TEXT NOT NULL,
    reserved_usd NUMERIC NOT NULL CHECK (reserved_usd > 0 AND reserved_usd <= 25),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'response_received', 'succeeded', 'failed', 'outcome_unknown')),
    attempt_id TEXT NOT NULL UNIQUE CHECK (attempt_id ~ '^[0-9a-f]{32}$'),
    dispatch_attempts INTEGER NOT NULL DEFAULT 0 CHECK (dispatch_attempts BETWEEN 0 AND 1),
    lease_token TEXT,
    lease_expires_at TIMESTAMPTZ,
    response TEXT,
    result TEXT,
    error TEXT CHECK (error IS NULL OR error ~ '^[a-z][a-z0-9_]{0,63}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    FOREIGN KEY (budget_scope, budget_key) REFERENCES model_budget_buckets(budget_scope, budget_key),
    CHECK ((lease_token IS NULL) = (lease_expires_at IS NULL)),
    CHECK (status <> 'running' OR lease_token IS NOT NULL),
    CHECK (status NOT IN ('queued', 'succeeded', 'failed', 'outcome_unknown') OR lease_token IS NULL),
    CHECK (status NOT IN ('response_received', 'succeeded') OR (response IS NOT NULL AND dispatch_attempts = 1)),
    CHECK ((status = 'succeeded') = (result IS NOT NULL)),
    CHECK ((status IN ('succeeded', 'failed', 'outcome_unknown')) = (finished_at IS NOT NULL))
);

CREATE INDEX model_jobs_claim ON model_jobs(status, created_at, job_id);
CREATE INDEX model_jobs_leases ON model_jobs(lease_expires_at) WHERE lease_token IS NOT NULL;
