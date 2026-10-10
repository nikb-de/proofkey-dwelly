# Mobile presentation design

The rejected version placed a desktop story rail and a rectangular content panel on a small viewport. The replacement makes the phone itself the presentation canvas: a 344×748 shell, 320×724 clipped screen, camera island, status area and home indicator. Hardware geometry is illustrative, not a claim to reproduce a particular device.

## Decisions

- **Safe areas and hierarchy:** a compact “Delivery help” header, order identity and one primary task per scene. [Apple: Layout](https://developer.apple.com/design/human-interface-guidelines/layout)
- **Touch controls:** each in-app button has at least a 44×44 logical-pixel hit area; a filled, rounded primary action remains above navigation. [Apple: Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons)
- **Navigation:** Messages, Delivery and Activity represent conversation, terms and receipt views. Five-step replay controls remain outside the app and are absent from capture mode. [Apple: Tab bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars)
- **Reading:** 24–26px scene titles and 14px primary message copy in a compact 320px screen. Secondary chrome is deliberately smaller; this is a filmed prototype, not a declaration of full HIG/accessibility compliance. No authoritative term is ellipsized. [Apple: Typography](https://developer.apple.com/design/human-interface-guidelines/typography)
- **Identity:** retain the existing forest/cream palette, local fonts, rounded cards and Right onTime branding. No generated image assets or third-party UI dependencies.

## Forty-second story

| Time | View | Evidence shown |
|---|---|---|
| 0–8s | Messages | Incoming request |
| 8–16s | Team review | Scripted plan or actual recorded model advice |
| 16–24s | Delivery | Requested versus offered date, time, handover and charge |
| 24–32s | Consent | Complete offer and explicitly replayed acceptance |
| 32–40s | Activity | Local booking receipt; physical delivery is not confirmed |

The LLM film replays existing responses; it does not call a provider while recording. Customer acceptance is replay navigation, not a new authenticated authorization. Both modes retain the source event and run details in the interactive viewer.

## Capture implementation

The logical canvas is 450×800. For crisp recording, Chromium renders it at CSS zoom 2 inside an actual 900×1600 video viewport, then exports to 1080×1920. Setting only device pixel ratio to 2 does **not** increase Chromium's video canvas content: a probe showed the 450×800 image padded into one quarter of the larger recording. The corrected physical-viewport approach was checked in a decoded frame before final recording.

The real server's CSP initially blocked an inline capture-mode initializer. Capture detection now runs in the allowed external JavaScript, and browser regression tests use the same CSP. This prevents presentation controls leaking into the filmed app.

## Clean audience-facing mode

The later `presentation=1` view removes Demo/Sandbox/Replay labels, model-run commentary and technical-detail controls from the film. Natural product labels replace that framing; original offer terms and source-backed decisions remain intact. It can be combined with `capture=1` for the phone-only composition. The default viewer retains provenance, and the clean export directory carries a separate provenance document. This is a visual presentation choice, not a change in execution status or a claim of real delivery.
