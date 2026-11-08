# QA-001 Source Health Navigation — CSS Root Cause and Fix

Date: 2026-11-08
Candidate: `integration/pr46-v2-rebase-20261108`

## Confirmed root cause

The desktop sidebar navigation (`.nav-link-item`) and mobile bottom navigation (`.mobile-tab-btn`) both declare `display: flex`. Their Source Health links are marked with the HTML `hidden` attribute and the role bootstrap correctly sets `element.hidden = !state.isAdmin`. However, the author-level component display declarations can override the browser's user-agent `[hidden] { display: none }` rule. This explains why the DOM/JavaScript role gate was present while the member still saw both links.

## Fix

`dashboard/styles.css` now declares a global `[hidden] { display: none !important; }` rule before component styles. This makes the semantic hidden state authoritative for every component, including admin-only sidebar and mobile navigation, while allowing JavaScript to unhide elements for administrator sessions.

A dashboard contract regression test asserts:
- both Source Health navigation variants are admin-only and retain the `hidden` attribute in markup;
- `.nav-link-item` and `.mobile-tab-btn` still use flex layout;
- the stylesheet explicitly enforces the hidden state with `display: none !important`.

## Verification status — browser retest completed 2026-11-08

**QA-001: PASS** on candidate commit `cf778c1f1da33c773f820cafea991fb084c58da8`.

- Member desktop: `#navSources`, `#sourcesSection`, and the mobile Source Health link had `display:none`, `hidden:true`, and zero-size geometry at 1536×900.
- Member mobile: Source Health remained hidden at 390×844, 375×812, and 320×740; member nav exposed Jobs/Applied/Preferences/Account only.
- Direct member `/dashboard/#sources` navigation settled at `/dashboard/#jobs`; Jobs active, Sources inactive, no flash observed.
- Member telemetry: no `/api/source-status`, `/api/source-status/summary`, or `/api/latency-summary` requests during a 35-second CDP capture.
- Member direct GETs to all three source-health endpoints returned 403.
- Admin desktop: Source Health nav and section visible at 1536×900.
- Admin mobile: Source Health nav and section visible at 390×844, 375×812, and 320×740.
- Admin direct GETs to all three source-health endpoints returned 200.

The browser report and complete result matrix are archived in `docs/QA/desktop-final-candidate-verification-2026-11-08.md`.

## Related QA-002 / QA-003 status

- Responsive metrics/layout: PASS for member and admin at 1536×900, 1280×800, 768×1024, 390×844, 375×812, and 320×740. No horizontal overflow or metric overlap; at 320px, “discovered” wraps to a second line but remains visible.
- Mobile bottom-navigation occlusion: BLOCKED. The browser pass could not retain a reliable obstruction rectangle or exported screenshot for archival verification.
- Screenshot artifact delivery: BLOCKED. Inline captures were taken, but no files could be exported from the browser control surface.
- Console smoke: PASS; no console errors or warnings observed in either context.
- Manual CSRF mutation tests: UNKNOWN; excluded by read-only scope.
- Session/logout/expiry mutation tests: UNKNOWN; excluded by read-only scope.

The report was performed against the synthetic-only candidate on port 18005. It did not change application code, configuration, database, shared dev, or production. Do not interpret the blocked evidence items as application defects; they are incomplete verification artifacts. Do not interpret UNKNOWN security checks as PASS.

## Separate 320px interaction failure — 2026-11-08

QA-001 remains PASS. A later, separate mobile interaction pass found a 320×740 hit-test failure while checking bottom-navigation/content accessibility. At this viewport, member `Mark Applied` hit-testing returned the “Newest First” button; admin hit-testing returned `.feed-status-strip`. The control rectangles were above the 56px bottom bar, which began at y=684, so the bottom bar is not yet established as the cause. At 390×844 and 375×812, both roles passed.

Detailed geometry and current evidence are in `docs/QA/desktop-final-visual-evidence-2026-11-08.md`. Root cause remains unconfirmed because the report lacks the exact hit-test coordinates, `elementsFromPoint()` stack and returned-element bounds/CSS. Do not change CSS speculatively. Obtain a second diagnostic pass, then add a focused regression and verify 320px after any fix. Screenshot file export is still BLOCKED; manual CSRF/session mutation checks remain UNKNOWN.
