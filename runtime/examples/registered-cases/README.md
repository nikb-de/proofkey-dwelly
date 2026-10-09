# Two independent synthetic cases

`window-request.json` and `window-fixture.json` request the 13:00–15:00 UTC window
on 2026-10-08 with permitted slots J06-S3 and J06-S4. The expected verified effect
is one reschedule to J06-S3. `goods-request.json` and `goods-fixture.json` request
whole-order refusal of two j06-widget units and one j06-cable unit, followed by
one return initiation to J06-DEPOT-B. Initiated means neither physically received
nor paid. All identities and proof strings are synthetic and public demo data.

The JSON files are literal inputs authored independently of the packaged builtin
fixtures. The empty operator packet catalog/access facts satisfy the existing
retained-source contract; they do not grant access to original documents.

Input fixtures must contain no actual carriage-return character (CR, U+000D):
use LF line endings, not CRLF or bare CR. Preparation rejects actual CR as
`invalid_input` before allocating any child. JSON-escaped `\r` inside strings
is accepted. This limit keeps the exact source bytes representable by the
existing admission consumer, whose text reads normalize actual CR/CRLF.
Preparation never normalizes accepted input; staging, hash and source declaration
retain the same exact bytes. The existing 1 MiB and nesting/declaration limits
also apply.

Keep the parent `registered_case_bootstrap.py` and this directory together outside
the installed package. In a trusted Python application with the package installed:

```python
from pathlib import Path
from proofkey.clock import SyntheticReplayClock
from registered_case_bootstrap import prepare_case, execute_case

data = Path('/absolute/path/to/registered-cases')
parent = Path('/absolute/private/fresh-parent')  # already exists, owner-only 0700
clock = SyntheticReplayClock()
request_path = data / 'window-request.json'
prepared, request = prepare_case(request_path, data / 'window-fixture.json', parent, clock)
print(prepared.summary())  # unapproved, path-free summary only
receipt = execute_case(prepared, request, request_path, clock, 'cli')
print(receipt['public'])
```

`execute_case` explicitly provisions demo review and transport authority; replace
that application policy only in a separately reviewed integration. It captures
a fresh configuration context and a fresh launch context. Use a fresh private
parent for each case and surface (`library` or `cli`). Retain failed/pending state;
never reset a claim or replay an executed preparation as a new operation.

If the library command raises, the example closes its actual dispatcher and
re-raises the original exception. Private `_j06_shutdown` and
`_j06_shutdown_error` attributes carry the actual close result or close error;
they are diagnostic application data, not a product wire interface. The
acceptance driver records preparation paths before execution and saves this
exceptional lifecycle evidence separately, marking missing or pending closure
as unverified. It never replaces a command error with a close error.

For reproducible offline acceptance, from the checkout run the existing source
interpreter with `runtime/scripts/verify_synthetic_provisioning.py --commit FULL_SHA
--wheelhouse ABSOLUTE_EXISTING_WHEELHOUSE --dependency-receipt ABSOLUTE_RECEIPT
--output ABSOLUTE_NEW_PRIVATE_DIRECTORY`. Arguments are explicit local paths;
the driver acquires no dependencies. It checks all 20 staged artifact hashes,
builds/inspects wheel and sdist, rebuilds from sdist, installs offline, then invokes
an isolated installed probe from scratch. Every run requires a new output path.
Raw evidence contains private paths/source/authority and must remain private.

No real reviewer, native service, money, model, ASR, migration, registered recovery,
reply/stop control, timed adaptation or other-platform capability is established.
