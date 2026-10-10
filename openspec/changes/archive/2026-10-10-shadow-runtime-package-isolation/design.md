## Root cause and choice

`qualify_factory.current_preflight` requires exactly86runtime package paths. New `proofkey/shadow.py` made87. Fresh two-test reproduction fails before the origin/helper tests run. An isolated copy excluding only that file passes with every retained hash unchanged.

Keep the established integrity contract. Move the helper to `tools/dwelly_bridge/runtime_binding.py`, using absolute imports from proofkey.contracts/identity/journal. Do not eagerly import it from bridge.__init__ or its CLI; runtime remains optional.

Update the two current test import sites and public documentation. Historical receipts remain historical. Add a quick direct current_preflight regression, then rerun all bridge/resolver tests and the two original failing qualification tests. A still-running longer test is not represented as passing.

Companion-specific resolver tests also belong under `tools/dwelly_bridge/tests/`, with an explicit optional-runtime skip when dependencies are absent. The documented standalone runtime-directory test invocation must not acquire a dependency on the repository-root `tools` package. Keep runtime source stable while qualification children are running; perform the test-only relocation after the current source-hold run ends.

Plan: corrective task appended to `docs/superpowers/plans/2026-10-10-model-runtime-shadow-bridge.md`.
