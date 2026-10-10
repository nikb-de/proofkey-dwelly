# Case 024-N1: Tracking says delivered but the recipient has no parcel (Case system in maintenance, registration unknown)

## Case details

- **Source role:** Delivery investigations, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-25 09:00:00 UTC
- **Escalated:** 2026-02-25 09:31:00 UTC
- **Updated:** 2026-02-25 11:20:00 UTC
- **Completed:** 2026-02-25 11:20:00 UTC
- **Primary shipment:** DL-024
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 024, events 001–003 retained; branch CHANNEL_FAILURE

## Context

DL-024 shows delivered at 08:10 UTC, but tracking support has not reviewed the handover record or route stop and has verified only the shipment and recipient account match. Sorin Vaal says no one in his household has the parcel and asks for a carrier investigation. This branch diverges after event 003: Case system in maintenance, registration unknown.

## Initial request

Automatic reply. Our case system is under maintenance until 11:00 UTC. Messages received during maintenance may not create a case. If no case reference reaches you, do not assume a case exists.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

After 11:00 UTC, ask Delivery investigations, Plover Arc Logistics, whether a case for DL-024 exists from the 09:25 request, before sending the request again.

- **Recipient:** Delivery investigations, Plover Arc Logistics
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The carrier confirms whether one case exists for DL-024; a registered case is not a finding.

## Boundaries and remaining work

Must not: Do not send a second investigation request now, and do not tell Sorin that an investigation is open.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
