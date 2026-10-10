## Why

The platform passes JSON-free evidence prompts through the shared provider adapter. OpenAI Responses rejects JSON-object mode when only `instructions`, but not `input`, mentions JSON. A root diagnostic reproduced HTTP 400 and succeeded when input explicitly requested JSON.

## What Changes

- Prefix OpenAI input with exactly `Return a JSON object.\n` while preserving the complete prompt as its suffix.
- Keep provider instructions, other providers, bounds, storage policy, dispatch count and runtime gates unchanged.
- Cover the provider's input-only constraint at the fake HTTP boundary; make no paid calls.

## Impact

Only the OpenAI request envelope and its tests change. No semantic ledger or persisted evidence mutation.
