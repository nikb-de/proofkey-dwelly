# Design

Use `design/right-ontime/prototype` as the visual reference: forest sidebar, paper background, restrained brass accents, Manrope/Inter, readable cards and role navigation. Preserve the current PostgreSQL API, revision bindings, idempotency, source provenance and human approval gates.

Team owns `/`, Customer owns `/customer.html`, Preparation owns `/preparation.html`. Each standalone screen uses `session.js` and existing APIs. Customer is explicitly an operator-assisted preview: a proposed window is a proposal, not independently verified consent or a confirmed carrier booking. Only a matching current execution receipt can show sandbox confirmation; it is never physical delivery confirmation. No invented slots, prices, names or live connector availability.

Preparation saves a draft locally, exports JSON and runs real read-only preflight checks against capabilities/cases. These checks are not provider calls, regression tests or activation. Requests derives records from persisted decisions, reviews, actions and source events, separating internal requests from unsent external messages. Unknown data is labelled unknown.

Parallel ownership: Team agent edits index/app/style and team-specific helpers/tests; Customer agent edits customer files/tests; Preparation agent edits preparation files/tests; coordinator edits serving routes, integration tests, specs and documentation. No shared mutable files between implementers.
