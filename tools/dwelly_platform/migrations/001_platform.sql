CREATE TABLE platform_decisions (
    sequence BIGSERIAL PRIMARY KEY,
    decision_id TEXT UNIQUE NOT NULL,
    case_id TEXT NOT NULL REFERENCES case_heads(case_id),
    revision INTEGER NOT NULL,
    record TEXT NOT NULL,
    FOREIGN KEY (case_id, revision) REFERENCES case_snapshots(case_id, revision)
);
CREATE TABLE platform_reviews (
    sequence BIGSERIAL PRIMARY KEY,
    review_id TEXT UNIQUE NOT NULL,
    decision_id TEXT NOT NULL REFERENCES platform_decisions(decision_id),
    case_id TEXT NOT NULL REFERENCES case_heads(case_id),
    record TEXT NOT NULL
);
CREATE TABLE platform_bookings (
    booking_id TEXT PRIMARY KEY,
    decision_id TEXT UNIQUE NOT NULL REFERENCES platform_decisions(decision_id),
    case_id TEXT NOT NULL REFERENCES case_heads(case_id),
    slot_start TEXT NOT NULL,
    slot_end TEXT NOT NULL,
    address_change BOOLEAN NOT NULL CHECK (address_change = false)
);
CREATE TABLE platform_actions (
    sequence BIGSERIAL PRIMARY KEY,
    action_id TEXT UNIQUE NOT NULL,
    decision_id TEXT UNIQUE NOT NULL REFERENCES platform_decisions(decision_id),
    booking_id TEXT UNIQUE NOT NULL REFERENCES platform_bookings(booking_id),
    case_id TEXT NOT NULL REFERENCES case_heads(case_id),
    record TEXT NOT NULL
);
CREATE TABLE platform_assets (
    sequence BIGSERIAL PRIMARY KEY,
    asset_id TEXT UNIQUE NOT NULL,
    case_id TEXT NOT NULL REFERENCES case_heads(case_id),
    sha256 TEXT NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    mime_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes > 0),
    filename TEXT NOT NULL,
    data BYTEA NOT NULL
);
CREATE TABLE platform_model_links (
    sequence BIGSERIAL PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    case_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    snapshot_hash TEXT NOT NULL,
    FOREIGN KEY (case_id, revision) REFERENCES case_snapshots(case_id, revision)
);
CREATE TABLE platform_requests (
    scope TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    body TEXT NOT NULL,
    result TEXT NOT NULL,
    PRIMARY KEY (scope, idempotency_key)
);
