# Licence and distribution status

[LICENSE](LICENSE) contains the standard Apache License 2.0 text for eligible original application code contributed to this project. [NOTICE.md](NOTICE.md) defines the material boundary. A licence file does not establish ownership, contributor grants, dataset permission or compliance by itself.

## Included source and separate terms

The repository includes the local platform, evaluation tools, frontend and [operational runtime](runtime/README.md). The runtime is subject to its own [rights inventory](runtime/RIGHTS.md), [notice](runtime/NOTICE) and dependency records. Earlier statements that the runtime was absent no longer describe this checkout.

Third-party Python packages, browser tooling, PostgreSQL, Docker base images and any redistributed assets retain their own terms and required notices. Platform dependency declarations include [requirements-postgres.lock](requirements-postgres.lock) and [requirements-platform.txt](requirements-platform.txt); the runtime has additional dependency declarations. These files record dependencies, not a complete audited licence/notice inventory. API services, model access, generated outputs and source data have separate terms.

## Data, fixtures and media

The [Dwelly public development package](data/dwelly-public-cases/README.md) includes copied source cases, attachments, normalized records and derived outputs. On **10 October 2026**, the user confirmed that the organisers permitted publication of the provided Dwelly cases and their derivatives. This is **user-attested permission**; no written grant or upstream dataset licence was independently inspected for this update. It supersedes the earlier unresolved-publication status for those materials. These materials and their derived excerpts are **not re-licensed under Apache-2.0**, and their original terms remain applicable.

Two intake tests retain source excerpts from public Dwelly examples: case 001 in [test_pilot.py](tools/dwelly_cases/tests/test_pilot.py) and case 023 in [test_validation.py](tools/dwelly_cases/tests/test_validation.py). They remain identified derivatives of the provided cases under the recorded publication permission, not newly owned Apache-2.0 material.

Authored/synthetic labels, imported case histories, screenshots, recordings, demo media, provider receipts and model outputs retain their own provenance and applicable terms. The recorded permission for provided cases and derivatives must not be generalized into a new licence for unrelated third-party material. A secret scan alone does not establish that all content is free of personal or confidential information.

## Publication scope and audit

The [submission audit](docs/submission-audit-2026-10-10.md) records the reviewed publication scope, history/secret review, cleanup and verification limits. Retain paths and hashes, origins, contribution scope, applicable terms and required notices. Preserve any restricted originals privately and do not silently re-license third-party materials.

On 10 October 2026, the user explicitly authorized making the existing repository, including its full Git history, public after audit and separately confirmed organiser permission for the provided cases and derivatives. This records the authorization and its source; it is not independent legal certification. See [submission requirement G](SUBMISSION.md#g-apache-20-and-third-party-rights) for the audit record and live publication status.
