# JobBeeper — Final Candidate Acceptance & Regression Verification

**Date:** 2026-11-08 (Asia/Calcutta)  
**Target:** `http://localhost:18005/dashboard/` only  
**Candidate:** `integration/pr46-v2-rebase-20261108`  
**Tested commit:** `cf778c1f1da33c773f820cafea991fb084c58da8`  
**CSS fix reference:** `f22616c`  
**Accounts:** synthetic member `qa-member@local.test` (id 2) and synthetic admin `qa-admin@local.test` (id 1). Credentials and session material omitted.

## Scope and controls

Two independent browser contexts were used (Chrome member context and isolated in-app admin context). Only GET/navigation, DOM inspection, screenshots, and browser Network/console observation were performed. No application code, configuration, or database was changed. No collector, OAuth, Telegram message, application submission, external host, or other port was used. No state-changing request was issued; therefore CSRF mutation and session/logout mutation verification are UNKNOWN by design.

## Results

| ID | Check | Actual evidence | Result |
|---|---|---|---|
| QA-001-M1 | Member desktop Source Health sidebar | At 1536×900, `#navSources`, `#sourcesSection`, and the mobile Source Health link had `display:none`, `hidden:true`, and zero-size geometry. | **PASS** |
| QA-001-M2 | Member mobile navigation | At 390×844, 375×812, and 320×740, Source Health remained hidden; member navigation exposed Jobs/Applied/Preferences/Account only. | **PASS** |
| QA-001-M3 | Member direct `#sources` route | `/dashboard/#sources` settled at `/dashboard/#jobs`; Jobs active and Sources inactive. No flash observed. | **PASS** |
| QA-001-M4 | Member telemetry polling | A 35-second CDP Network capture after login contained no requests to `/api/source-status`, `/api/source-status/summary`, or `/api/latency-summary`. | **PASS** |
| QA-001-M5 | Member direct API GETs | Fresh authenticated GETs returned 403 for all three source-health endpoints. | **PASS** |
| QA-001-A1 | Admin desktop Source Health | At 1536×900, `#navSources` was visible (215.2×35.5) and `#sourcesSection` visible (1296×844). | **PASS** |
| QA-001-A2 | Admin mobile Source Health | At 390×844, 375×812, and 320×740, the Source Health link and section were visible; body scroll width equaled viewport width. | **PASS** |
| QA-001-A3 | Admin source-health APIs | `/api/source-status` 200; `/api/source-status/summary` 200; `/api/latency-summary` 200. | **PASS** |
| QA-002-R | Responsive metric layout | Member and admin measured at 1536×900, 1280×800, 768×1024, 390×844, 375×812, and 320×740. Body scroll width equaled viewport width. Metric boxes did not overlap; at 320px, “discovered” wrapped to a second line but remained visible. | **PASS** (minor wrap) |
| QA-002-O | Mobile bottom-navigation occlusion | Viewport/scroll inspection was attempted, but no reliable exported screenshot or stable bottom-navigation obstruction rectangle was available for archival verification. | **BLOCKED** |
| QA-002-S | Screenshot artifact delivery | Inline browser captures were taken for desktop, admin/member mobile, and Source Health states. CUA exposed image captures but no writable filesystem export path/bytes. Requested screenshot directory remained without image files. | **BLOCKED** |
| QA-003-C | Console regression smoke | Fresh member/admin console error and warning reads were empty. | **PASS** |
| QA-003-N | CSRF negative tests | Not run: read-only acceptance scope prohibited state-changing requests. | **UNKNOWN** |
| QA-003-S | Session/logout/expiry mutation checks | Not run in this read-only pass. | **UNKNOWN** |

## Network and console evidence

- Member `/api/auth/me`: authenticated synthetic member, role `user` (id 2).
- Admin `/api/auth/me`: authenticated synthetic administrator, role `admin` (id 1).
- Member source-health endpoint GET statuses: 403, 403, 403.
- Admin source-health endpoint GET statuses: 200, 200, 200.
- Member telemetry observation window: 35 seconds; matching requests: none.
- Console errors/warnings: none observed in either context.

## Viewport measurements

At 1536×900, 1280×800, 768×1024, 390×844, and 375×812, all four metric labels/values were on one visible row with no horizontal overflow. At 320×740, body width remained exactly 320px; “discovered” wrapped below “Today” while “matched” and “alerted” remained visible. No overlap or clipping was observed.

## Screenshot evidence

The requested local directory was `C:\Users\avibh\Documents\Codex\JobBeeper-QA-Context\screenshots\final-candidate-2026-11-08\`. Browser captures were taken during viewport and auth-state checks, but the browser control surface did not expose a writable screenshot export. No fabricated or unredacted screenshots are included. Screenshot attachment therefore remains BLOCKED and must be rerun with a capture/export-capable harness.

## Acceptance disposition

The fresh authorization, navigation, telemetry, API-status, responsive-layout, and console checks PASS. **Final acceptance remains BLOCKED** because screenshot files and reliable archival evidence for mobile bottom-navigation occlusion could not be exported in this browser pass. CSRF/session mutation checks remain UNKNOWN because they were intentionally excluded from the read-only scope.

## Next actions

1. Repeat only the screenshot/evidence portion with a capture-capable local browser harness. Save redacted PNGs for desktop, member/admin mobile, and the bottom of a scrolled mobile page.
2. Verify bottom-navigation occlusion at 390×844, 375×812, and 320×740 using stable element rectangles plus hit-testing at the bottom of the content area. Record actual measurements and screenshots; do not infer PASS from viewport-width checks.
3. Run a separately scoped, controlled CSRF/session mutation test only against the isolated synthetic QA instance, or explicitly retain these checks as release UNKNOWN. Do not run mutation tests against shared dev or production.
4. Keep PR #51 draft and do not promote to shared dev until the evidence gates, CI for the final code head, and explicit owner approval are satisfied.
