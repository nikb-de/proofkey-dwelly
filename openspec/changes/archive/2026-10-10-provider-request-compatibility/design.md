# Design

`proposal_prompt` and `judge_prompt` add `output_format: json_object` to the
host-owned outer payload. The payload remains JSON, visible-only, and blinded.
The transport must not append hidden text: the budgeted/persisted prompt must
equal the actual outbound input.

An Anthropic seat may declare `workspace_id_env`. Configuration contains the
variable name, never an account ID or key. The transport accepts only an ASCII
environment name and a value matching `wrkspc_[A-Za-z0-9]{1,128}`. Explicit missing
or empty values fail as `missing_workspace_id`; malformed values fail as
`invalid_workspace_id`, before HTTP dispatch. Whitespace-only values are malformed,
not empty. The optional field is forbidden on
other providers. Omission retains the old behavior for workspace-scoped keys.

Preflight is presence-only and reports missing workspace configuration separately
from missing API credentials. It does not authenticate or validate billing. The
example config opts in using `ANTHROPIC_WORKSPACE_ID`; users with scoped keys may
remove that field. Private local environment setup remains outside Git.

No retries or provider substitutions are introduced. A two-case, three-provider
smoke experiment will verify actual runner integration, not holdout accuracy or
human-calibrated quality. Raw case outputs and credentials remain private.

The first integrated smoke returned all eight API responses, but both Claude
judgments were rejected because they used a single outer `json` Markdown fence.
Normalize this envelope only at the model-output parser. Retain exact raw text
in receipts; use the existing strict JSON decoder and schema validation after
removing one complete outer fence. Do not extract objects from prose, repair
malformed JSON, accept multiple blocks, or weaken case/config JSON readers.
