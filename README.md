# ProofKey — Dwelly Delivery & Logistics

Private development package for an offline logistics assistant. **This is not a complete hackathon submission.** The repository contains architecture documentation, 50 public development cases with raw source files, separated agent/reference JSON, and preserved deterministic pilot outputs. Runnable project source, licensing clearance, the demo video and unseen-case results remain pending.

Start here: [architecture](docs/architecture.md), [pilot verification](docs/pilot-verification.md), [data package and information boundaries](data/dwelly-public-cases/README.md), [pilot summary](data/dwelly-public-cases/pilot/summary.json), [answer layout](ANSWERS/README.md), [missing demo video](DEMO/README.md), [submission checklist](SUBMISSION.md), and [licence status](LICENSE-STATUS.md).

The raw source and evaluation records contain future information. **Do not give an agent the entire repository.** A proposer may receive only its own decision-time `data/dwelly-public-cases/agent/<case>.json` and explicitly allowed visible assets; evaluation and raw source stay separate.

## 1. What we built

ProofKey has a private offline logistics runtime and a separately staged next-action pilot. The runtime has two fixed synthetic replay demonstrations: delivery-window rescheduling and whole-order goods refusal with return initiation. The pilot reads development cases up to an escalation, freezes a deterministic next-communication proposal, then compares routing against a later example.

The included pilot artifacts contain 50 unsent drafts, zero operational effects and 11/50 recipient-and-channel routing matches against recorded examples. This is a routing proxy, not semantic accuracy; semantic assessment is unassessed. The pilot source and private runtime remain outside this repository. Neither path establishes a native Dwelly integration or general logistics coverage.

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

See the [current architecture and boundaries](docs/architecture.md). The private runtime is described for context, not shipped as runnable code in this package.

## 4. How to run

There is no runnable project source in this repository yet. The included JSON and reports are inspectable artifacts, not a working installation. After the separately reviewed pilot is included, its documented interface is Python 3.11+ with no third-party package dependencies:

```sh
python3 -B -m tools.dwelly_cases import --source SOURCE_REPO --output NEW_BUNDLE --expected-cases 50
python3 -B -m tools.dwelly_cases run --bundle NEW_BUNDLE --output NEW_RESULTS
python3 -B -m unittest discover -s tools/dwelly_cases/tests -v
```

`SOURCE_REPO` denotes a local checkout of the public cases. Output directories must be new and outside the source tree. This repository includes a [pinned private data copy](data/dwelly-public-cases/README.md) and preserved outputs, but no pilot implementation or private runtime. These commands describe the separately staged pilot; they cannot run from this repository alone today.

## 5. Models, APIs and external services

The staged pilot uses deterministic rules and local files. It needs no model account, API key, environment variable or external service. The private runtime uses offline simulations for its demonstrated path. Model adapters or interface definitions are not evidence of live provider participation. No live Dwelly, messaging, payment or logistics connection is asserted.

## 6. Assumptions

The staged pilot expects the supported Delivery & Logistics history format and a defined escalation cutoff. Only events and attachment references available at that point may influence its proposal; later records are held for evaluation. The raw/agent/evaluation/pilot directories are an explicit separation convention, not an enforced security sandbox. Public examples are already-seen development material, and a recorded later action is one reference example rather than a unique correct answer.

Case text and channel labels are contextual evidence, not independently authenticated permission. The intended code licence is Apache-2.0 after ownership and contribution rights are established for the exact included files. Public availability of a dataset is not a redistribution licence.

## 7. Known limitations

Routing agreement is a proxy and does not establish semantic correctness, safety, authorisation or physical completion. Semantic assessment is explicitly unassessed. No unseen Reality Test has been run for this scaffold, and no results are invented.

The pilot handles one track and a bounded history format; it does not understand arbitrary attachments or perform multimodal reasoning. All six public raw attachments occur after the decision cutoff and are not agent-visible inputs. Proposals do not send messages, reserve slots, create returns, issue refunds or transfer ownership. The repository lacks runnable source, the standard code licence, the actual demo video and generated unseen answers. Private conversations, private Drive originals, runtime artifacts, credentials and the parent Git history are excluded. The copied public data remains private/internal: no upstream dataset licence was identified, and no redistribution clearance or Apache re-licensing is asserted.

## 8. What we would improve next

Include reviewed source and reproducible installation instructions after the file-level rights review. Then broaden supported source formats, conduct independent semantic review, establish native authority contracts, add tested integrations, and measure a complete-batch rehearsal. Produce and review the working-product video and generate all unseen-case outputs with the frozen system. Record evidence for each completed step before expanding the supported scope.
