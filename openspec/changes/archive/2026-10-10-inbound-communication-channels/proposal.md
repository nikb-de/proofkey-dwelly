# Inbound communication channels

## Why
The platform accepts manually authored events and uploaded media, but has no durable channel ingress. Team testing needs email, chat, call transcripts and recordings to enter the same case without inventing sender authority or claiming a real provider connection.

## What Changes
- Add a versioned generic inbound envelope and bounded RFC822 parser.
- Add configured conversation/contact mappings, durable inbox receipts, quarantine, replay and atomic promotion to canonical case events/assets.
- Add signed loopback webhook ingress, operator import API, CLI configuration and an English Communications UI.
- Keep media processing explicit and paid providers disabled by default.

## Capabilities
### New Capabilities
- `inbound-communications`: authenticated local channel ingress and case-bound promotion.

## Impact
Additive tables and API/UI; canonical v1 event/dataset contracts do not change. No live email, chat or telephony account is connected and no outbound sends/calls are implemented.
