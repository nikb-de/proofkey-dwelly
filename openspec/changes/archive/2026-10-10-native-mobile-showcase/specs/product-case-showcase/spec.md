## MODIFIED Requirements
### Requirement: Presentation-ready responsive interface
The replay SHALL use the existing Right onTime identity and local assets, a rounded clipped native-style mobile app composition, legible mobile and desktop layouts, one primary moment per scene, accessible navigation and an always-visible replay/sandbox label.

#### Scenario: Recording is presented
- **WHEN** a 40-second mobile recording is exported
- **THEN** five source-backed scenes are presented for eight seconds each inside a rounded phone shell with status area, safe areas and native-style navigation
- **AND** each primary control has a minimum 44×44 logical-pixel hit area and primary content fits without clipping
- **AND** both the scripted and recorded-model variants retain their provenance
- **AND** the export contains exactly 1,200 frames at 30 fps, with no new model calls or operational writes
