# Design

`presentation=1` is an explicit view mode, compatible with `capture=1`. It removes technical framing from the audience-facing phone screen and uses product copy such as “Delivery assistant” and “Accept these terms.” Business terms, dates, handover requirements and booking status remain accurate. It must never relabel the final booking as delivered.

The standard replay remains evidence-rich. Presentation files retain external provenance in capture/export manifests and the handoff document, instead of repeating it inside the film. Raw source JSON, historical model receipts, validation, authority gates and runtime contracts are unchanged. The visible acceptance still navigates the read-only presentation and does not create consent or dispatch requests.

Use TDD for clean-screen coverage and default-view regression. Re-record both variants with the existing five-by-eight-second capture contract and verify decoded midpoint frames.
