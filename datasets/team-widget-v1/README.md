# Team widget development sources

The manifest pins unchanged authored sources at commit `c361245eaad4361f7b886adc56f05dd56d4807b3`. It covers 51 documents: cases 001–050 and the 002-N4 branch, with 286 snapshot cutoffs. Namespaced IDs distinguish these cases from the legacy sixteen-cutoff development set. Related 002 branches are not independent cases; labels remain unvalidated author annotations.

The platform catalog includes both groups. `load_catalog(group='legacy')` preserves legacy-only experiment selections. Observed messages preserve copied recipient IDs; optional `author_limits` preserves the selected snapshot's limits as untrusted author context, never runtime policy or authorization. Projection excludes future messages and annotation/state labels.

## Export

```sh
PYTHONPATH=.:tools:runtime/src python -m tools.dwelly_analysis export --group team --output /tmp/proofkey-team-export
```

Choose a new output directory. `--group team` exports 286 separated input/reference pairs; `--group all` exports 302. Omitting the option preserves the original 16 legacy cutoffs. These are development snapshots, not 302 independent cases or a calibrated held-out benchmark. Related source families must remain together when designing future splits.
