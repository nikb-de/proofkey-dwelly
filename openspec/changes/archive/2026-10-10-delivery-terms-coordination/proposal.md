# Delivery terms coordination backend

## Why

The principal case requires cancellation, renegotiated terms and explicit acceptance; a same-address reschedule alone cannot represent that workflow or distinguish a booking request from its confirmed outcome.

## What Changes

Implement the main case-001-terms backend path requested on 10 October: confirmed cancellation, versioned replacement terms, explicit acceptance, booking request and separate Dispatch readback. Preserve the existing rescheduling API and local-only trust boundary. The frozen source and preparation findings are in docs/demos/2026-10-10-case-001-terms/README.md.

No real courier, payment or outbound communication integration is introduced. No new paid model calls are required for implementation verification.
