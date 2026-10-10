# Architecture rendering fix

## Why
The current architecture overview clips Mermaid node text in the user's document viewer. Earlier standalone SVG bounds checks did not cover host styling or font changes.

## What changes
- Replace the six live Mermaid embeds in the two active architecture documents with fixed rendered PNG previews.
- Preserve the exact Mermaid source and standalone SVG alongside every preview.
- Verify previews at narrow and desktop widths and retain the renderer limitations explicitly.

## Impact
Documentation and diagram assets only. No runtime, model, policy, credential or provider changes.
