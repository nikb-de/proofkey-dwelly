## ADDED Requirements

### Requirement: Source-backed product replay
The platform SHALL offer a read-only five-scene product replay of case-001, with separate scripted and recorded-model modes, based on captured backend evidence.

#### Scenario: Replay is opened
- **WHEN** a user opens a supported showcase mode
- **THEN** the UI displays the originating case, recorded source messages and historical model advice without executing business actions or new model calls
- **AND** earlier scenes do not reveal later confirmation or model responses

### Requirement: Terms and authority remain clear
The replay SHALL distinguish requested terms from offered terms, consent from booking confirmation, and local booking confirmation from physical delivery.

#### Scenario: Customer reviews the changed offer
- **WHEN** the offer is displayed
- **THEN** the changed delivery window, recipient-only handover and no-charge condition are explicit
- **AND** any acceptance control is labelled as replay navigation, not authenticated consent

### Requirement: Presentation-ready responsive interface
The replay SHALL use the existing Right onTime identity and local assets, legible mobile and desktop layouts, one primary moment per scene, accessible navigation and an always-visible replay/sandbox label.

#### Scenario: Recording is presented
- **WHEN** a 50-second mobile recording is exported
- **THEN** the primary surface shows product interactions rather than raw logs or administrative forms
- **AND** both the scripted and recorded-model variants retain their provenance
