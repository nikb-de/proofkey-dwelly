# Design

Add a versioned coordination aggregate alongside existing case decisions. Store each accepted command and aggregate snapshot in PostgreSQL; append its explicitly labelled internal audit event to the canonical case in the same transaction. Existing source events remain immutable. The workflow is read through case detail and dedicated same-origin routes. Model projection therefore receives source context and internal workflow evidence through immutable case events, without live mutable context or author labels.

All writes require expected_revision, snapshot_hash and expected_workflow_version. A body-bound idempotency key returns the original result. A new source event invalidates consent for a new booking request; the final Dispatch response is a new evidence event correlated with the outstanding request. State cannot be completed by a model assertion or merely sending a message.

Local operator commands are attestations, not authenticated customer or carrier acts. Dispatch evidence must be a visible message from the configured declared dispatch actor, addressed to the case operator. Recipient consent evidence must be from the linked customer. Requests and readbacks are simulated/recorded locally with zero external effects.

Terms are strict: slot_start, slot_end, handover (recipient_only or concierge_allowed), recipient_present, charge {amount_minor,currency}. New slots must be timezone-aware, future, <=8h; old source dates remain historical and are not made executable by disabling checks. Offer hash/version and explicit acceptance bind every term. A changed offer clears acceptance.

States: booked, cancellation_pending, awaiting_terms, awaiting_consent, ready_to_book, booking_pending, booking_confirmed, escalated. Completion means booking confirmed, physical_delivery remains unconfirmed.
