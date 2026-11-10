# Desktop scheduler QA follow-up — 2026-11-10

## Source report

Reviewed the owner-uploaded JOBBEEPER_SCHEDULER_DESKTOP_QA_2026-11-10.md.

Its original disposition was BLOCKED with PASS 10 / FAIL 0 / BLOCKED 6 / UNKNOWN 4. The report established:
- Admin scheduler panel and authenticated admin API match: 10 active boards, 8 providers, 7 hosts; max 3 concurrent hosts, max 1 active board per host, 5-second host spacing.
- Ten board rows and seven host rows render with successful outcomes, zero failure streaks and clear baselines.
- Member /api/auth/me identified a member, Source Health navigation was absent, and member GET /api/discovery/scheduler/status returned 403.
- Member layout was tested at 1440, 1024, 768, 390 and 320 widths without horizontal overflow.
- No member console errors/warnings were seen.
- Anonymous 401, admin post-handoff viewport/reload, and exported screenshot evidence were left blocked/unknown because the connected Termalin browser surface could not open a clean anonymous context, could not maintain separate authenticated admin/member contexts after handoff, and did not provide a screenshot export path.

## Independent follow-up: anonymous authorization

PASS — anonymous scheduler endpoint returns HTTP 401.

Executed a direct GET with no Cookie or Authorization header against the isolated candidate:
- Target: http://127.0.0.1:18011/api/discovery/scheduler/status
- Response status: HTTP/1.1 401 Unauthorized
- Response body: {"detail":"Authentication required."}
- No scheduler payload was returned.

This closes the anonymous 401 evidence gap at the HTTP/API layer. It does not claim an anonymous browser screenshot or visual capture; the earlier Termalin browser limitation still applies to that kind of UI evidence.

## Follow-up browser runner attempt and safety disposition

A separate Chromium/Playwright container image was started to independently run two authenticated contexts, test hard-reload persistence, visit five viewport sizes and write screenshot files. Chromium and Playwright installed into a disposable Docker build stage, but Docker image export did not complete after a prolonged stall. The build was stopped rather than continuing to consume memory/swap on the JobBeeper VM. No Playwright browser test was run and no screenshots are claimed.

Two automation-only QA accounts were temporarily created in the candidate DB for this attempted run:
- id 3 qa-auto-admin@jobbeeper.test
- id 4 qa-auto-member@jobbeeper.test

Both are now disabled. Their temporary credential file was removed. The owner-created QA accounts (id 1 admin and id 2 member) remain active and unchanged. No passwords were written to the repo or returned in chat.

## Revised evidence disposition

| Check | Result | Evidence / note |
|---|---|---|
| Admin scheduler API and panel | PASS | Owner Desktop report, SCH-ADM-001 |
| Per-board rows and due-time formatting | PASS | Owner Desktop report, SCH-ADM-002 |
| Shared host budget rows | PASS | Owner Desktop report, SCH-ADM-003 |
| Existing Source Health panels | PASS | Owner Desktop report, SCH-ADM-004 |
| Member identity and Source Health hidden | PASS | Owner Desktop report, SCH-MEM-001/002 |
| Member scheduler endpoint | PASS | Owner Desktop report, SCH-MEM-003: 403 |
| Member viewport matrix | PASS | Owner Desktop report: 1440/1024/768/390/320, no overflow |
| Member console errors/warnings | PASS | Owner Desktop report: none observed |
| Anonymous scheduler endpoint | PASS | Independent no-cookie HTTP GET: 401 |
| Admin hard reload / persisted UI state | UNKNOWN | Owner report did not perform the reload; no independent browser run completed |
| Admin responsive matrix after handoff | BLOCKED | Independent authenticated browser viewport run did not complete |
| Exported screenshot files | BLOCKED | No browser screenshot export was produced |
| Candidate service/data safety | PASS | Health 200; DB integrity ok; 10 latest board outcomes successful; zero sent notifications; temp automation accounts disabled |

Updated counts: PASS 11 / FAIL 0 / BLOCKED 5 / UNKNOWN 4. One previously blocked check (anonymous HTTP 401) is now proven. The Desktop release recommendation remains BLOCKED until admin reload/viewport evidence and screenshot artifacts are supplied.

## Current candidate state after follow-up

- Candidate container: job-radar-board-scheduler-qa, loopback 127.0.0.1:18011.
- Container restart count remained zero at the last runtime inspection.
- Health endpoint returned 200.
- SQLite integrity: ok.
- Jobs: 1,902 at the last inspection.
- Ten active board schedules; all ten latest outcomes successful.
- Sent notifications: zero.
- Original owner QA admin/member accounts remain active; automation-only ids 3/4 are disabled.
- Existing dev, connector-QA, synthetic-QA and production containers were not changed.

## Next agent / owner actions

1. Use ChatGPT Desktop (or the owner's local Playwright installation) to sign in as the owner-created QA admin in an independent browser context.
2. Hard reload Source Health and capture the scheduler panel after reload. Compare board/host rows against the authenticated API after reload.
3. Test admin viewports 1440x900, 1024x768, 768x1024, 390x844 and 320x740. Keep any table scrolling inside its own container and record document/body widths.
4. Export real PNG screenshots to files, with filenames and a short index; do not claim in-memory screenshots as exported artifacts.
5. Keep the independent anonymous 401 and member 403 checks in the report as already proven.
6. Return the new report and screenshot files for engineering review. Do not change board activation, source config, notifications or preferences during evidence collection.
7. Keep PR #66 draft and stacked on PR #65. No merge or deployment is authorized by these QA results alone.
