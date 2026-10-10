## 1. Model contract
- [x] 1.1 Implement strict profiles, dedicated evidence-only prompt and validated model candidates with provider receipts.
- [x] 1.2 Prove reference isolation, conservative output validation, failure handling and redaction with mocked transports.
## 2. PostgreSQL transactions
- [x] 2.1 Add explicit schema migration, idempotent submission and atomic budget reservation.
- [x] 2.2 Add fenced dispatch/response/result lifecycle, recovery and real PostgreSQL concurrency tests.
## 3. Runtime and UI
- [x] 3.1 Wire opt-in model API and bounded worker into the existing server without changing offline behavior.
- [x] 3.2 Add profile selection, polling, safe retry and readable transaction details.
## 4. Verify and deliver
- [x] 4.1 Run regression, browser QA, independent review and credential preflight. No provider is eligible locally: real canaries NOT_RUN, explicitly deferred until keys are supplied.
- [x] 4.2 Document configuration/results/limits and archive the completed implementation spec. Commit as verified local work; do not merge main or change cloud resources.
