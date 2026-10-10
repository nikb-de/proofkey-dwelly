# Design

Use `design/right-ontime/prototype/client.html` and `assets/style.css` as the visual source. Restore the 640px shell, forest header with order badge, request title, one delivery card, parcel context, in-card two-step progress and compact secondary actions. Missing proposal data gets a calm empty state, not a required manual timestamp/evidence form.

The current CustomerSession remains the authority for binding and submission. A displayed current proposal supplies its existing evidence references; the customer never selects internal event IDs. Manual requests, when used, remain explicitly operator-assisted and do not grant customer identity or permission. Stop actions must not pretend to cancel backend work; disclose unsupported cancellation or only abandon an unsent local draft.

All copy is English. GET status refresh does not trigger another model or operational action. Show reviewed preferences as preferences, not bookings. Preserve stale conflicts, unknown responses and draft recovery.
