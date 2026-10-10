## 1. Source replay and state oracle
- [x] 1.1 Build leakage-free source cutoff replay and an independently specified state/check ledger.
- [x] 1.2 Qualify checks against good/bad/missing-output controls and document source independence.
## 2. Actual API runner
- [x] 2.1 Implement bounded live/simulated HTTP E2E, durable readback, replay and stale-revision probes with artifacts.
- [x] 2.2 Verify real PostgreSQL and explicit scripted transport; run live canaries only when credentials are available. Live preflight is unavailable; no keys were present and no live request was made.
## 3. UI work control
- [x] 3.1 Render coordination and execution metadata separately; add safe read-only job polling and recovery tests.
## 4. Integrated evidence
- [x] 4.1 Run authored-case browser E2E, independent review, regression and document actual results/limits.
- [x] 4.2 Archive the completed specification; record unavailable live coverage separately if keys remain missing. Live provider results remain unavailable and are not acceptance evidence.
