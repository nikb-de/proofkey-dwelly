# Restore the approved customer design

## Why
The current customer screen preserves branding but replaces the approved compact delivery experience with an operator-style evidence form. Functional tests did not detect this design regression.

## What changes
- Reuse the final Right onTime customer composition, typography, spacing and components.
- Keep technical identifiers and evidence selection out of the main customer flow.
- Show actual proposals and their exact times; explicitly represent missing availability, price and booking confirmation.
- Preserve snapshot validation, idempotency, human review and sandbox-only boundaries.
- Add rendered-browser assertions and compare desktop/mobile screenshots against the approved source.

## Scope
Customer UI and a small Team presentation alignment; no backend authorization changes, new integrations or fabricated outcomes. Live evaluation is an independent verification task and does not change gold labels.
