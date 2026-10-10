# ProofKey — Dwelly Delivery & Logistics

Preparation scaffold for an offline logistics assistant. **This is not a complete hackathon submission.** Source inclusion, licensing, the demo video and unseen-case results remain pending. The private repository currently contains only this documentation scaffold.

Scaffold records: [answer layout](ANSWERS/README.md), [missing demo video](DEMO/README.md), [submission checklist](SUBMISSION.md), and [licence status](LICENSE-STATUS.md).

## 1. What we built

ProofKey has a private offline logistics runtime and a separately staged next-action pilot. The runtime has two fixed synthetic replay demonstrations: delivery-window rescheduling and whole-order goods refusal with return initiation. The pilot reads development cases up to an escalation, freezes a deterministic next-communication proposal, then compares routing against a later example.

The pilot produces unsent drafts and makes no operational calls. Its source is staged separately for rights review and is not yet part of this repository. The demonstrations do not establish a native Dwelly integration or general logistics coverage.

## 2. Operational problem

Logistics requests arrive across messages, records and attachments, often with missing context, conflicting facts or unclear authority. A useful next action must respect what is actually known and who can authorise the change. ProofKey explores how to keep a proposed action, permission to act, an attempted operation and a verified result distinct, while preserving unresolved work for review.

## 3. Architecture

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

## 4. How to run

There is no runnable source in this scaffold yet. The directory layout is not a working installation. After the separately reviewed pilot is included, its documented interface is Python 3.11+ with no third-party package dependencies:

```sh
python3 -B -m tools.dwelly_cases import --source SOURCE_REPO --output NEW_BUNDLE --expected-cases 50
python3 -B -m tools.dwelly_cases run --bundle NEW_BUNDLE --output NEW_RESULTS
python3 -B -m unittest discover -s tools/dwelly_cases/tests -v
```

`SOURCE_REPO` must be a separately obtained local checkout of the public cases. Output directories must be new and outside the source tree. The case dataset, generated bundles and private runtime are not included. These commands describe the staged pilot, not a claim that they run from this scaffold today.

## 5. Models, APIs and external services

The staged pilot uses deterministic rules and local files. It needs no model account, API key, environment variable or external service. The private runtime uses offline simulations for its demonstrated path. Model adapters or interface definitions are not evidence of live provider participation. No live Dwelly, messaging, payment or logistics connection is asserted.

## 6. Assumptions

The staged pilot expects the supported Delivery & Logistics history format and a defined escalation cutoff. Only events and attachment references available at that point may influence its proposal; later records are held for evaluation. Public examples are already-seen development material, and a recorded later action is one reference example rather than a unique correct answer.

Case text and channel labels are contextual evidence, not independently authenticated permission. The intended code licence is Apache-2.0 after ownership and contribution rights are established for the exact included files. Public availability of a dataset is not a redistribution licence.

## 7. Known limitations

Routing agreement is a proxy and does not establish semantic correctness, safety, authorisation or physical completion. Semantic assessment is explicitly unassessed. No unseen Reality Test has been run for this scaffold, and no results are invented.

The pilot handles one track and a bounded history format; it does not understand arbitrary attachments or perform multimodal reasoning. Its proposals do not send messages, reserve slots, create returns, issue refunds or transfer ownership. The repository currently lacks runnable source, the standard licence, the actual demo video and generated unseen answers. Private conversations, original documents, attachments, credentials, generated case bundles and the parent Git history are excluded.

## 8. What we would improve next

Include reviewed source and reproducible installation instructions after the file-level rights review. Then broaden supported source formats, conduct independent semantic review, establish native authority contracts, add tested integrations, and measure a complete-batch rehearsal. Produce and review the working-product video and generate all unseen-case outputs with the frozen system. Record evidence for each completed step before expanding the supported scope.
