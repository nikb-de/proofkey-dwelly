# Verification and limits

Verified on 10 October 2026:

- 9 decision snapshots, 3 independent synthetic source families, 3 episodes; all development, all assistant-authored and unreviewed.
- 13 validator tests pass, including corruption, leakage, split contamination, traversal, missing dependencies, history tampering and false review status.
- Package validator passes with **0 eligible reviewed rows**.
- All 8 copied canonical schemas are byte-identical to `contracts/v1/schemas/` at source commit `cdd94bd`.
- All 9 generated snapshots reproduce exactly through actual `CaseStore.create/append` in temporary storage; standalone regeneration is byte-identical.
- The existing 20 backend contract tests pass.
- All 21 relative documentation links stay inside the kit and resolve.
- Independent review approved the format and safeguards after correcting detached-package links.

Reproduce from this directory:

```sh
python3 -m pip install -r requirements.txt
python3 scripts/validate.py .
python3 -m unittest discover -s tests -v
```

The dependency-install command may access the package index; the validator and tests themselves do not contact providers or resolve schemas over the network. The supplied distribution contains an additional `PACKAGE_INTEGRITY.json` with exact-byte SHA-256 values for the packaged files. These hashes detect corruption relative to the inventory, not the authenticity of source claims.

This is **format and structural validation**, not label calibration or model evaluation. No semantic grader, training exporter, fine-tuning job, complete episode simulator, real media extraction, runtime integration or sealed holdout is included. No live provider call or business effect occurred. Real-case permissions and human reviewer identity require independent team verification.
