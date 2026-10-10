CREATE TABLE platform_coordination (
    sequence BIGSERIAL PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES case_heads(case_id),
    version INTEGER NOT NULL CHECK (version > 0),
    record TEXT NOT NULL,
    UNIQUE (case_id, version)
);
