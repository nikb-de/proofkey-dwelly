# product-case-showcase Specification

## Purpose
Present the source-backed case-001 journey in separate scripted and historical-model replay modes, with clear consent, authority and sandbox boundaries.
## Requirements
### Requirement: Source-backed product replay
The platform SHALL offer a read-only five-scene product replay of case-001, with separate scripted and recorded-model modes, based on captured backend evidence.

#### Scenario: Replay is opened
- **WHEN** a user opens a supported showcase mode
- **THEN** the UI displays the originating case, recorded source messages and historical model advice without executing business actions or new model calls
- **AND** earlier scenes do not reveal later confirmation or model responses

### Requirement: Terms and authority remain clear
The replay SHALL distinguish requested terms from offered terms, consent from booking confirmation, and booking confirmation from physical delivery. The audit view and exported artifact provenance SHALL identify simulated interactions. A clean presentation MAY omit in-frame technical labels but SHALL NOT invent external execution or completed delivery.

#### Scenario: Customer reviews the changed offer
- **WHEN** the offer is displayed
- **THEN** the changed delivery window, recipient-only handover and no-charge condition are explicit
- **AND** acceptance remains read-only navigation without creating authenticated consent or an operational request
- **AND** the default audit view labels that interaction as replay navigation while clean-film documentation retains the same qualification outside the frame

### Requirement: Presentation-ready responsive interface
The replay SHALL use the existing Right onTime identity and local assets, a rounded clipped native-style mobile app composition, legible mobile and desktop layouts, one primary moment per scene and accessible navigation. The default audit view SHALL identify replay and sandbox provenance. An explicit clean presentation mode SHALL omit technical framing from the audience-facing UI while preserving accurate business terms and separate artifact provenance.

#### Scenario: Recording is presented
- **WHEN** a 40-second mobile recording is exported
- **THEN** five source-backed scenes are presented for eight seconds each inside a rounded phone shell with status area, safe areas and native-style navigation
- **AND** each primary control has a minimum 44×44 logical-pixel hit area and primary content fits without clipping
- **AND** both scripted and recorded-model variants retain provenance in the capture manifest and handoff, without inventing live execution or physical delivery
- **AND** the export contains exactly 1,200 frames at 30 fps, with no new model calls or operational writes

#### Scenario: Clean presentation mode is selected
- **WHEN** the viewer uses `presentation=1`
- **THEN** the visible app has no Demo, Sandbox, Replay, provenance or technical-detail controls
- **AND** product-oriented labels replace technical narration without rewriting source terms or historical advice
- **AND** the default audit view and raw evidence remain available outside that presentation

### Requirement: Replay evidence integrity
The replay builder SHALL validate each snapshot's canonical content hash and each recorded model input's complete equality with the platform's evidence projection at that snapshot, including the canonical input hash. Coordination SHALL reference an existing captured snapshot at or before the scene cutoff with a matching revision and hash. Nested coordination records and their evidence SHALL not exceed that historical cutoff, and an offer's recorded terms hash SHALL match its complete terms. Valid older coordination SHALL remain usable when a scene contains newer messages.

#### Scenario: Model input content changes without changing event IDs
- **WHEN** a recorded model input changes a message body, actor, timestamp, order or other projected field, with either a stale or recomputed input hash
- **THEN** the builder rejects the capture instead of presenting the model as bound to the original source cutoff

#### Scenario: Coordination comes from a later or mismatched snapshot
- **WHEN** an early scene contains future coordination, a mismatched coordination snapshot hash, a future nested record or evidence outside the coordination cutoff
- **THEN** the builder rejects the capture

#### Scenario: An offer changes while its recorded hash remains unchanged
- **WHEN** recorded offer terms do not match their canonical terms hash
- **THEN** the builder rejects the capture

#### Scenario: Valid historical captures are rebuilt
- **WHEN** a scene contains valid older coordination and the unchanged original source/model records
- **THEN** the builder preserves that history and produces the same replay bundle bytes
