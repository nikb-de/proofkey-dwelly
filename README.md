# ProofKey — Dwelly Delivery & Logistics

Preparation scaffold for an offline logistics assistant. **This is not a complete hackathon submission.** Source inclusion, licensing, the demo video and unseen-case results remain pending. The private repository currently contains only this documentation scaffold.

## What the project does

ProofKey explores how an assistant can propose a useful next action while distinguishing a request, permission to act, an attempted operation and a verified result. The current private runtime has two fixed synthetic replay demonstrations: delivery-window rescheduling and whole-order goods refusal with return initiation. These examples do not establish a native Dwelly integration or general logistics coverage.

A separately prepared standard-library pilot reads Dwelly Delivery & Logistics development cases up to an escalation, freezes a deterministic next-communication proposal, and then compares routing against a later example. Its proposals are unsent drafts; it makes no operational calls. The pilot source is staged separately for rights review and is not yet part of this repository.

## Architecture

```text
Public development case folders
  -> bounded importer: visible events and available attachments
  -> deterministic baseline: proposed next communication, no effects
  -> frozen proposal
  -> separate later-reference reader
  -> contract checks and routing-agreement proxy

Private synthetic runtime
  -> typed request -> policy and authority gates -> offline adapters
  -> intent journal -> postcondition verification -> answer export
```

The pilot and private runtime are separate paths. No automated bridge between arbitrary public case text and the runtime is claimed. A channel label or case narrative does not grant authenticated authority.

## Prerequisites, installation and running

There is no runnable source in this scaffold yet. Do not interpret the directory layout as a working installation. After the separately reviewed pilot is included, its documented interface is Python 3.11+ with no third-party package dependencies:

```sh
python3 -B -m tools.dwelly_cases import --source SOURCE_REPO --output NEW_BUNDLE --expected-cases 50
python3 -B -m tools.dwelly_cases run --bundle NEW_BUNDLE --output NEW_RESULTS
python3 -B -m unittest discover -s tools/dwelly_cases/tests -v
```

`SOURCE_REPO` must be a separately obtained local checkout of the public cases. Output directories must be new and outside the source tree. The case dataset, generated bundles and private runtime are not included. These commands describe the staged pilot, not a claim that they run from this scaffold today.

## Models, APIs and configuration

The staged pilot uses deterministic rules and local files. It needs no model account, API key, environment variable or external service. The private runtime uses offline simulations for its demonstrated path. Model adapters or interface definitions are not evidence of live provider participation. No live Dwelly, messaging, payment or logistics connection is asserted.

## Evaluation and limits

The public examples are already-seen development material. Their later actions are reference examples, not unique gold answers. Routing agreement is a proxy and does not establish semantic correctness, safety, authorisation or physical completion. Semantic assessment is explicitly unassessed. No unseen Reality Test has been run for this scaffold, and no results are invented.

The pilot handles one track and a bounded history format; it does not understand arbitrary attachments or perform multimodal reasoning. Its proposals do not send messages, reserve slots, create returns, issue refunds or transfer ownership. Known future work includes broader source formats, independent semantic review, native authority contracts, actual integrations and a measured complete-batch rehearsal.

## Submission materials and rights

- [ANSWERS/README.md](ANSWERS/README.md) describes the required output layout; there are no submitted answers.
- [DEMO/README.md](DEMO/README.md) records the missing in-repository video.
- [SUBMISSION.md](SUBMISSION.md) contains the open submission checklist and unfilled metadata.
- [LICENSE-STATUS.md](LICENSE-STATUS.md) explains why an Apache licence is not yet applied to unresolved source or data.

The intended code licence is Apache-2.0 after ownership and contribution rights are established for the exact included files. Public availability of a dataset is not a redistribution licence. Private conversations, original documents, attachments, credentials, generated case bundles and the parent Git history are excluded.
