# Independent installation design review

Date: 2026-10-09. Reviewer: separate local agent `installation_design_review`, configured `gpt-6.1-sol`, high reasoning. This is not a five-provider assessment, served-model attestation or human approval.

Scope: proposed `installed-offline-resources` child and installation discovery, compared with relevant source at baseline `bf83ed92c3209b6b1d10819370f1ed9be9d74e57`. Read-only; no product edits, tests, builds, installation, downloads or environment creation.

## Reviewer result

Approve narrowly at design level; no load-bearing defect found.

The two-root relocation matches existing source assumptions. It preserves host `_pinned` validation, separate writable state, the ten-name allowlist, historical factory vectors and existing admission coverage. Resource hashes and the current `profiles.py` pin agree with the inspected baseline.

## Limits

Implementation correctness, dependency acquisition, actual distribution contents and installed execution remain unverified. User design and dependency-acquisition approval remain pending. J13 and J14 are still open. The root independently checked the four recorded resource hashes and strict OpenSpec validation succeeded; schema validation does not establish runtime behavior.
