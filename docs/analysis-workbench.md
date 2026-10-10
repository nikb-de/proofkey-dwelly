# Case-state analysis workbench

The colleague's [case-state widget](https://github.com/nikb-de/proofkey-dwelly/tree/8fbcd1fb633efa248e4045765a7854138118127d/case-state-widget) is integrated as a **separate local development interface**. It combines the source timeline, a step-bound evidence projection, a limited offline baseline and an explicitly separate author reference. Nothing here sends messages, submits business forms or changes the live Cloud SQL case store. Paid model proposals are available only with explicit server-side opt-in; see [model analysis operations and contracts](model-analysis-operations.md). Offline startup below needs no provider or PostgreSQL connection.

## Run

From the repository root, with Python 3.11+:

```sh
python3 -m tools.dwelly_analysis serve --port 8093 --runs-dir /tmp/proofkey-analysis-runs
```

Open [http://127.0.0.1:8093](http://127.0.0.1:8093). Select a case and step, inspect the evidence-only input, then click **Analyze this step · offline**. The run is saved locally and can be downloaded. The source timeline is unchanged by analysis. The source viewer's standalone imports remain browser-local and do not add files to the trusted server catalog.

If `--runs-dir` is omitted, the service uses a temporary directory; capabilities disclose this. It is loopback-only and deliberately refuses Cloud Run environment markers. Do not publish it to the internet or disable these checks. No API keys are needed or accepted by the browser. The existing private Cloud Run case API and its authentication remain unchanged.

## What was imported

| Source | Selected states, including start | Qualification |
| --- | ---: | --- |
| Original case 002 | 6 | Authored state annotations over synthetic source |
| 002 N4 channel failure | 8 | Related negative branch, same independence family |
| Minimal example | 2 | UI/control fixture, not an independent business evaluation |

**16 selectable snapshots are not 16 independent cases.** All are development records; no untouched holdout, reviewed training rows or semantic-accuracy claim is created. Raw JSON is preserved byte-for-byte and checked against [the source manifest](../datasets/case-state-widget-v1/manifest.json). Source commit: `8fbcd1fb633efa248e4045765a7854138118127d`. The source widget code has local validation/import hardening; its original code hashes remain provenance, not a claim that the hardened files are unchanged.

## Analysis boundary

The baseline is a small deterministic evidence-pattern recognizer, not an LLM and not a general logistics policy engine. It handles a recorded outgoing request, supplied apartment information, ambiguous form submission and explicit service confirmation. Other evidence may return unknown/operator review. Its inferred `completed` state concerns the supplied coordination goal, never physical delivery or verified business execution.

Completion recognition uses two closed full-message grammars based on the supplied fixtures. Additional or conflicting sentences abstain. This conservative implementation is a plumbing baseline, not evidence of generalization to new wording or cases.

The UI labels author snapshots, generated candidate and literal comparison separately. A matching author state only means agreement with that draft annotation. It is not a calibrated judge score. The default offline path never invokes a provider. The optional model path has separate PostgreSQL jobs, receipt/usage details and safe replay; it does not invoke the legacy multi-judge benchmark or any operational adapter.

## Export for the team

```sh
python3 -m tools.dwelly_analysis export --output /tmp/proofkey-state-dataset-new
```

Use a new directory: exports never overwrite an existing package. Share the entire package, not a merged input/reference JSON. Read [the analysis contract](../contracts/analysis-v1/README.md) for exact records, hashes, endpoints, exclusions and the explicit incompatibility with the old next-contact runner.

A [checked-in development package](../datasets/case-state-widget-v1/README.md) is ready for team inspection and review. Its inputs, references and manifest have been reread and verified against the source projection.

Before using these records for training/evals: have the responsible reviewer validate intended state/action and ambiguity, add independent case families and allocate splits by family. A controlled evidence-only state-analysis model adapter now exists, but its outputs and agreement are not validated gold labels. The current source format allows dynamic actor discovery and channels/timestamps absent from frozen intake v1; no silent conversion is performed.

## Checks

```sh
python3 -m unittest discover -s tools/dwelly_analysis/tests -v
node --test case-state-widget/tests/*.test.mjs
```

Browser smoke covers all selections, run/download, stale-response isolation and narrow-screen layout. Offline and browser checks validate the implementation, not model quality or production readiness.
