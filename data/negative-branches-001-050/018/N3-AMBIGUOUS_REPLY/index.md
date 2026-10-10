# Case 018-N3: Shipment is approaching its return-to-sender deadline (Recipient agrees without naming option)

## Case details

- **Source role:** Nalo Vere, recipient
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-19 09:00:00 UTC
- **Escalated:** 2026-02-19 09:35:00 UTC
- **Updated:** 2026-02-19 10:15:00 UTC
- **Completed:** 2026-02-19 10:15:00 UTC
- **Primary shipment:** DL-018
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 018, events 001–003 retained; branch AMBIGUOUS_REPLY

## Context

The Exception desk reports that DL-018 enters return-to-sender processing at 16:00 UTC on 2026-02-19 unless the customer selects redelivery or depot collection on 2026-02-20, both currently available. No choice is recorded, and the desk asks Iona to contact authorised recipient Nalo Vere before the cutoff. This branch diverges after event 003: Recipient agrees without naming option.

## Initial request

Yes, tomorrow is fine for me. Just make sure it does not go back to the sender. I have been waiting for it all week.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask Nalo once on the same call whether to choose redelivery on 2026-02-20 or depot collection on 2026-02-20.

- **Recipient:** Nalo Vere, recipient
- **Channel:** Call transcript
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** ASK_CUSTOMER (workflow sheet A)

## Outcome

Nalo names one option and the Exception desk applies it before 16:00 UTC; the return is cancelled only when the desk confirms it.

## Boundaries and remaining work

Must not: Do not record redelivery because 'tomorrow is fine' sounds like a home delivery; Nalo has not chosen an option.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
