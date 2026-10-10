## Decision

Use the shared OpenAI adapter boundary, because callers outside the semantic evaluation runner do not necessarily include JSON wording. A fixed format instruction plus the unchanged prompt works for all those callers without changing evidence serialization. OpenAI `instructions` stays separate. Anthropic and Gemini payloads retain their current exact envelopes.

## Verification

A boundary double returns HTTP 400 for JSON-object requests whose input lacks the word JSON, even when instructions include it. The same request must succeed after the prefix, retain the exact prompt suffix, and dispatch once. Existing transport envelope/error/boundary tests must remain green. Live verification remains the parent's separate authorized task.
