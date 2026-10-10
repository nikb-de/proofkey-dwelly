# Post-hoc official answer assessment

Goal: review the exact 30 already-published answers without re-solving cases,
changing answers or implying that the earlier reliability pilot graded them.

1. Freeze all original `ANSWERS/` bytes. Prepare a separate, reference-free packet
   containing decision-time input, the original answer/reasoning and status.
2. Reuse the eight rubric anchors and current provider transports. Test the
   wrapper offline, with missing output represented separately from a score.
3. Run 30 cases through three API profiles, at most six calls concurrently,
   with durable intents, no retries and USD 25 per-model reservation caps.
4. Preserve raw requests and responses. Report per-case scores, critical flags,
   abstentions, failures and disagreement; do not manufacture a consensus truth.
5. Independently recheck original hashes and publication safety. Publish only
   the separate auxiliary assessment and archive its specification.

The whole-answer reviewer framing is not the earlier action-only calibration
prompt. Its grades remain unvalidated model opinions. No operational or
official answer file is changed, and no external business action is performed.
