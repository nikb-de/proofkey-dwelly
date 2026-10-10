CREATE TABLE case_heads (
    case_id TEXT PRIMARY KEY,
    current_revision INTEGER NOT NULL CHECK (current_revision BETWEEN 0 AND 128)
);
CREATE TABLE case_snapshots (
    case_id TEXT NOT NULL REFERENCES case_heads(case_id),
    revision INTEGER NOT NULL CHECK (revision BETWEEN 0 AND 128),
    snapshot TEXT NOT NULL,
    PRIMARY KEY (case_id, revision)
);
CREATE TABLE case_requests (
    scope TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    body TEXT NOT NULL,
    case_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    PRIMARY KEY (scope, idempotency_key),
    FOREIGN KEY (case_id, revision) REFERENCES case_snapshots(case_id, revision)
);
CREATE TABLE analysis_outbox (
    job_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    snapshot_hash TEXT NOT NULL CHECK (snapshot_hash ~ '^[0-9a-f]{64}$'),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'leased', 'completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    lease_token TEXT,
    lease_expires_at TIMESTAMPTZ,
    worker_id TEXT,
    UNIQUE (case_id, revision),
    FOREIGN KEY (case_id, revision) REFERENCES case_snapshots(case_id, revision),
    CHECK ((status = 'leased' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL AND worker_id IS NOT NULL)
        OR (status <> 'leased' AND lease_token IS NULL AND lease_expires_at IS NULL AND worker_id IS NULL))
);
CREATE INDEX analysis_outbox_claim ON analysis_outbox(status, created_at, job_id);
