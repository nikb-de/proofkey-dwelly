## MODIFIED Requirements
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
