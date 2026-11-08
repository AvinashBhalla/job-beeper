# JobBeeper — Final Visual Evidence and Mobile Navigation Occlusion

**Date:** 2026-11-08 (Asia/Calcutta)  
**Target:** `http://localhost:18005/dashboard/` only  
**Candidate:** `integration/pr46-v2-rebase-20261108`  
**Tested commit:** `cf778c1f1da33c773f820cafea991fb084c58da8`

## Method and boundaries

Two independent authenticated synthetic contexts were used: member and administrator. The connected Chrome/IAB Playwright surface was used for viewport resizing, DOM geometry, internal scroll-container inspection and `elementFromPoint()` hit-testing. Only GET/navigation and read-only DOM operations were performed. No state-changing requests, code/config/database changes, collectors, OAuth, Telegram or external services were used.

## Mobile navigation geometry and hit testing

The fixed element was `.mobile-bottom-navigation`. It was visible in every role/viewport, with `position: fixed`, `z-index: 99`, `display: flex`, `visibility: visible`, `left: 0`, and `right` equal to viewport width. Height was 56px.

| Role | Viewport | Nav top/bottom/height | Internal list max/final scroll | Final Mark Applied rect (top–bottom) | Hit-test result | Result |
|---|---:|---:|---:|---:|---|---|
| Member | 390×844 | 788 / 844 / 56 | 336 / 336 | 476.05–499.65 | `SPAN` descendant “Mark Applied” | **PASS** |
| Member | 375×812 | 756 / 812 / 56 | 399 / 399.2 | 428.38–451.98 | `SPAN` descendant “Mark Applied” | **PASS** |
| Member | 320×740 | 684 / 740 / 56 | 686 / 685.6 | 259.75–283.35 | `BUTTON` “Newest First” (not intended control) | **FAIL** |
| Admin | 390×844 | 788 / 844 / 56 | 282 / 281.6 | 561.50–585.10 | `SPAN` descendant “Mark Applied” | **PASS** |
| Admin | 375×812 | 756 / 812 / 56 | 345 / 344.8 | 513.83–537.43 | `SPAN` descendant “Mark Applied” | **PASS** |
| Admin | 320×740 | 684 / 740 / 56 | 616 / 616 | 360.40–384.00 | `.feed-status-strip` (not intended control) | **FAIL** |

At 390px and 375px, the final interactive control was fully above the navigation bar and hit-testing resolved to the intended control descendant. At 320px, the final control's reported rectangle was also above the navigation bar, but hit-testing resolved to another page element in both roles. The mismatches are different by role (`Newest First` in the member context; `.feed-status-strip` in the admin context). This is a real failed acceptance assertion; it is not evidence that the bottom navigation itself overlaps the button.

The issue is reproducible by opening the candidate dashboard at the stated 320×740 viewport, scrolling `#jobsListContainer` to maximum, and hit-testing the center of the final `Mark Applied` button. The supplied report does not contain the hit-test x/y coordinates, `elementsFromPoint()` stack, or bounds of the element returned by the hit test. Therefore the exact overlay/coordinate cause is **not yet established**.

Document width remained equal to viewport width in the sampled states. The relevant feed is inside `#jobsListContainer`; document `scrollY` alone is not sufficient for this check.

## Result matrix

- Member 390×844: **PASS**.
- Member 375×812: **PASS**.
- Member 320×740: **FAIL** — hit-test resolves to `Newest First` rather than the final `Mark Applied` control.
- Admin 390×844: **PASS**.
- Admin 375×812: **PASS**.
- Admin 320×740: **FAIL** — hit-test resolves to `.feed-status-strip` rather than the final `Mark Applied` control.
- Screenshot artifact export: **BLOCKED**.

## Screenshot artifact limitation

Inline browser captures were requested at 1536×900 for member/admin and 390×844, 375×812 and 320×740 for both roles. The connected browser returned screenshot bytes as an in-memory `Uint8Array`, but exposed no filesystem export method or writable path. The available `pageAssets` capability lists/bundles existing page assets and does not export viewport screenshots. The requested local directory was `C:\Users\avibh\Documents\Codex\JobBeeper-QA-Context\screenshots\final-candidate-2026-11-08\`; actual PNG inventory is empty. PNG signature, dimensions and byte-size validation are therefore **BLOCKED**. No PNGs were fabricated or claimed to exist.

## Other prior checks — unchanged

- QA-001 authorization, routing and telemetry: PASS.
- Responsive metric layout (no horizontal overflow or metric overlap): PASS.
- Console smoke: PASS.
- Manual CSRF/session mutation checks: UNKNOWN because the test remained read-only.

## Next actions

1. Diagnose both 320px hit-test mismatches before changing CSS. At the exact measured center of `Mark Applied`, capture viewport x/y, its full `getBoundingClientRect()`, `document.elementsFromPoint(x,y)` stack with tag/id/class/text, and each hit element's rectangle, computed position/z-index/pointer-events/opacity/visibility. Also record the containing `.opportunity-row`, `#jobsListContainer`, toolbar, status strip and navigation rectangles.
2. Repeat the hit test immediately after the rectangle is read and again after a short stable frame interval; verify the button is still connected to the current DOM. This separates a true overlay from a stale element/reference or coordinate-space error.
3. Test the same coordinates in the member and admin contexts at 320×740; do not use 390/375 results to infer the 320px outcome.
4. Implement a minimal fix only after the stack/geometry identifies the cause. Add a regression test and rerun the 320px check as well as 390/375.
5. For screenshots, use a Playwright runner with `page.screenshot({ path: ... })` or equivalent local export capability; validate the PNG files after writing.
6. Keep PR #51 draft and do not promote to shared dev while the 320px interaction test is failing or the release gates remain unresolved.