

## 2026-11-08 — Final visual evidence follow-up: 320px interaction failure

- Added report `docs/QA/desktop-final-visual-evidence-2026-11-08.md` after a second read-only browser run against the synthetic candidate at `http://localhost:18005/dashboard/`, candidate branch `integration/pr46-v2-rebase-20261108`, code SHA `cf778c1f1da33c773f820cafea991fb084c58da8`.
- Member/admin 390×844: PASS. Member/admin 375×812: PASS. Member 320×740: FAIL because hit-testing at the final `Mark Applied` control returned `BUTTON` “Newest First”. Admin 320×740: FAIL because hit-testing returned `.feed-status-strip`.
- At 320×740 the fixed `.mobile-bottom-navigation` is 56px high with top y=684. Final target rectangles are member y=259.75–283.35 and admin y=360.40–384.00, above the nav. Therefore this is not proven to be bottom-bar occlusion; likely a separate overlay, stale element or coordinate-space problem. The exact x/y, `elementsFromPoint()` stack and returned element bounds/styles are missing. Root cause is explicitly UNCONFIRMED.
- Screenshot captures were returned as in-memory `Uint8Array` but the browser surface has no filesystem export path; screenshot directory contains no PNGs. Screenshot artifact delivery remains BLOCKED. Do not claim images exist.
- Prior QA-001 authorization/routing/telemetry PASS, responsive metrics layout PASS, console smoke PASS remain unchanged. Manual CSRF/session mutations remain UNKNOWN.
- No application code, config, database or runtime change was made in this evidence-only pass. No collector, OAuth, Telegram, shared-dev or production state was touched.
- **Next:** run exact coordinate/stack diagnostics at 320px in both member/admin contexts; inspect target and returned element bounding boxes/computed styles; verify DOM connectivity and repeat the hit test on stable frames. Make only a root-cause-supported minimal code fix and add regression. Then retest 320/375/390, export PNGs through a local Playwright filesystem-capable runner, verify CI, and only then seek explicit shared-dev approval. PR #51 remains draft.
