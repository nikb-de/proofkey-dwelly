## Investigation

The screenshot shows case `tst`, order `order-1`, customer `customer`, and operator `operator`. This payload passes same-realm validation. A Node VM-created equivalent fails because `keys()` compares its prototype to the validator's own `Object.prototype`. This proves a compatibility defect, not the exact embedded-browser root cause: direct automation of the `file://` tab was denied by browser policy and was not bypassed.

## Decisions

1. Recognize a plain record structurally: it must be an object, and its immediate prototype must be null or itself terminate at null. This accepts ordinary records across realms and null-prototype dictionaries, but rejects arrays and class instances. Require the exact own-key count and individual key membership; never compare comma-joined keys or rely on inherited fields.
2. Identify declaration errors by safe field names and constraints, never submitted values. Keep the existing UI's draft-preserving failure path.
3. Test real validator code with `node:vm` for foreign prototypes. Keep actual embedded-browser verification explicitly pending until the user retries.

## Risks and boundaries

This is not an assertion that all embedded-browser incompatibilities are resolved. Blob handling, IndexedDB, and decoding behavior are unchanged. Do not clear or migrate the user's local database or draft.
