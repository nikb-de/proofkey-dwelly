# Provider request compatibility

## Why

Live probes isolated two request-construction defects: the OpenAI Responses
JSON-mode input did not explicitly name JSON, and the Anthropic Messages request
omitted workspace selection required by an organizational key. Credentials were
accepted in corrected diagnostic requests; those corrections must be persistent.

## What changes

- Include a host-owned JSON output-format marker in proposal and judge payloads
  before budget admission and request persistence.
- Support an optional Anthropic-only `workspace_id_env` setting. Resolve and
  validate it at the transport boundary; preserve old workspace-scoped keys.
- Report missing configured workspace variables in offline preflight without
  exposing their values. Document CLI and Docker setup.
- Decode a single outer JSON Markdown fence in model replies while preserving
  the raw receipt and all strict JSON/schema validation. The first integrated
  smoke exposed this additional formatting incompatibility in both Claude replies.

## Impact

Only `tools/dwelly_model`, its tests and usage documentation change. No operational
runtime behavior, model identity, rubric, budget ceiling, or business effect changes.
