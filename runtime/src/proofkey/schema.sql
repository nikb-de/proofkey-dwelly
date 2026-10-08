CREATE TABLE schema_meta(version INTEGER NOT NULL CHECK(version > 0));
INSERT INTO schema_meta VALUES(1);
CREATE TABLE cases(case_id TEXT PRIMARY KEY, checkpoint_json TEXT, revision INTEGER NOT NULL CHECK(revision >= 0));
CREATE TABLE requests(case_id TEXT NOT NULL REFERENCES cases(case_id), generation TEXT NOT NULL,
 binding_json TEXT NOT NULL, versions_json TEXT, stop_requested INTEGER NOT NULL DEFAULT 0 CHECK(stop_requested IN (0,1)),
 request_id TEXT NOT NULL, request_revision TEXT NOT NULL, consent_revision TEXT NOT NULL, fingerprint TEXT NOT NULL,
 PRIMARY KEY(case_id,generation), UNIQUE(case_id,request_id,request_revision,consent_revision));
CREATE TABLE original_requests(case_id TEXT NOT NULL, generation TEXT NOT NULL, request_json TEXT NOT NULL,
 PRIMARY KEY(case_id,generation), FOREIGN KEY(case_id,generation) REFERENCES requests(case_id,generation));
CREATE TABLE intents(action_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, generation TEXT NOT NULL,
 fingerprint TEXT NOT NULL, intent_json TEXT NOT NULL,
 dispatch_state TEXT NOT NULL CHECK(dispatch_state IN ('prepared','dispatching','verified','rejected','pending','outcome_unknown','conflict')),
 verification_json TEXT, FOREIGN KEY(case_id,generation) REFERENCES requests(case_id,generation));
CREATE TABLE campaigns(permit_hash TEXT PRIMARY KEY, campaign_id TEXT NOT NULL UNIQUE,
 permit_json TEXT NOT NULL, consumed_json TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision >= 0));
CREATE TABLE invocations(invocation_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, generation TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('extraction','transcription','planning')), permit_hash TEXT NOT NULL REFERENCES campaigns(permit_hash),
 reservation_json TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('consumed','outcome_unknown','completed','failed')),
 receipt_json TEXT, FOREIGN KEY(case_id,generation) REFERENCES requests(case_id,generation));
CREATE TABLE entries(entry_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, generation TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('effect','provider','read','disclosure_read')), subject_id TEXT,
 lease_json TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('active','settled','overrun')),
 FOREIGN KEY(case_id,generation) REFERENCES requests(case_id,generation));
CREATE TABLE waits(question_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, generation TEXT NOT NULL,
 wait_json TEXT NOT NULL, FOREIGN KEY(case_id,generation) REFERENCES requests(case_id,generation));
CREATE TABLE transfers(transfer_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, generation TEXT NOT NULL,
 transfer_json TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('prepared','pending','accepted','outcome_unknown','rejected')),
 FOREIGN KEY(case_id,generation) REFERENCES requests(case_id,generation));
CREATE TABLE results(case_id TEXT NOT NULL, generation TEXT NOT NULL, result_json TEXT NOT NULL,
 PRIMARY KEY(case_id,generation), FOREIGN KEY(case_id,generation) REFERENCES requests(case_id,generation));
CREATE TABLE audit(sequence INTEGER PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id), event_json TEXT NOT NULL);
