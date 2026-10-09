## Why

An integrator currently has to read several nested receipts to distinguish host execution, reported effect verification, publication and owner closure. A short, content-free view can make the supported offline path understandable without inventing transport evidence or exposing case content.

## What Changes

- Add a bounded, side-effect-free projection of an existing CLI receipt into a typed correlated execution trace.
- Add an explicit stdin-only renderer, separate from the existing CLI, with JSON and Markdown output.
- Add a short outcome-first quickstart and verify it against fresh synthetic captures.
- Preserve unknown dispatch and unobserved original readback, independent publication and shutdown, and all invalid/pending positions.

## Capabilities

### New Capabilities
- `safe-evidence-trace`: bounded receipt projection, content-free rendering and supported-path documentation.

### Modified Capabilities

None. The default CLI, runtime authority and persisted schemas do not change.

## Impact

New detached modules and tests in `runtime/`, a linked quickstart, and verification evidence. No dependencies, network calls, collector, authority, business behavior or live integrations are added. This is a J23/J24 leaf; J08's complete support review and J21's human onboarding study remain separate.
