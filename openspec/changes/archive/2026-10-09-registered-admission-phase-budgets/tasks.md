## 1. Parent-bounded observation timing

- [x] 1.1 Preserve real regression RED for a slow successful engine operation.
- [x] 1.2 Implement shared observation phase without changing original authority.
- [x] 1.3 Add expiry, non-renewal, clock and context regressions; verify GREEN.
- [x] 1.4 Run module and full runtime suite; retain baseline failures by name.
- [x] 1.5 Obtain independent spec/quality review and resolve important findings.
- [x] 1.6 Record verification and archive only this completed leaf change.

Implementation: `15453e1`. Focused 34/34 and independent 3/3 passed. Full
runtime: 1,622 tests, 1 failure, 16 errors; exactly the 17 prior selectors,
zero new/removed. This is a bounded fix, not a green full-runtime qualification.
One minor boundary coverage opportunity is retained in the verification note.
