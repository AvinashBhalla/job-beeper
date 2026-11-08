
## Latest verified state — 2026-11-08 (320px hit-test failure; no promotion)

- Follow-up browser evidence is archived in `docs/QA/desktop-final-visual-evidence-2026-11-08.md`. It tested only the synthetic QA candidate at `http://localhost:18005/dashboard/`, branch `integration/pr46-v2-rebase-20261108`, code SHA `cf778c1f1da33c773f820cafea991fb084c58da8`.
- Mobile navigation/content check: member and admin at 390×844 PASS; member and admin at 375×812 PASS; member and admin at 320×740 FAIL. At 320px member target hit-test returned “Newest First”; admin returned `.feed-status-strip` instead of the final “Mark Applied” control.
- At 320×740 the fixed nav is 56px tall, top y=684. The reported target button rectangles (member y=259.75–283.35; admin y=360.40–384.00) are well above the bar. The bottom nav itself is not established as the cause. Exact hit-test x/y, elementsFromPoint stack, and hit element bounds/styles are absent; root cause remains UNCONFIRMED.
- Screenshot export remains BLOCKED: browser returned in-memory `Uint8Array` bytes but no writable path. PNG inventory in the requested directory is empty. Do not report screenshots as saved.
- QA-001 auth/routing/telemetry PASS, metric responsive layout PASS, console smoke PASS. Manual CSRF/session mutations remain UNKNOWN.
- No code/config/database/runtime state was modified; no collector, OAuth, Telegram, shared-dev or production action occurred. PR #51 must remain draft; no promotion until the 320px failure is diagnosed/fixed and reverified, screenshot evidence handled, security unknowns reviewed and CI green.
- Next: get exact 320px coordinate/stack diagnostics in both roles; distinguish stale DOM/coordinate-space errors from a true overlay; apply a minimal evidence-based fix with regression; rerun mobile 320/375/390; export PNGs via local Playwright; re-check CI and then seek explicit owner promotion approval.
