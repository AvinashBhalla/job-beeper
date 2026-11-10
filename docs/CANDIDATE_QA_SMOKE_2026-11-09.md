# Per-board scheduler candidate smoke test — 2026-11-09

## Environment isolation

- Image: `job-radar-board-scheduler:candidate` (`sha256:ce49a66bb795f730de8753b8baff75cd1a0f690440c37f309bf0bded8cd7cf74`).
- Container: `job-radar-board-scheduler-qa`.
- Listener: `127.0.0.1:18011` (loopback only; a private Termalin internal-site link was created for owner access).
- Database volume: `job-radar-board-scheduler-qa-data`, created for this candidate and not shared with dev or connector QA.
- Read-only config mount: `/tmp/job-radar-board-scheduler-candidate-config.json`.
- `notifications_enabled=false`; LinkedIn, Naukri, Instahyre and Hirebase are disabled; only the explicitly configured public ATS boards are enabled at a 3,600-second QA cadence. No Telegram credentials or Hirebase key were passed to the candidate.
- Candidate runtime config was seeded into its new volume at config version 17 before first startup. This was necessary because the application's intentional old-runtime migration disables new opt-in ATS sources when a fresh runtime config is first created; seeding the explicit QA config avoids unintentionally testing an all-disabled setup.
- Container restart count: 0. Existing dev, connector-QA, synthetic-QA and production containers were not changed.

## Candidate API and asset checks

- `GET /health` → HTTP 200, `{"status":"ok","version":"2.0.0",...}`.
- `GET /dashboard/` → HTTP 200 (`text/html`).
- `GET /dashboard/app.js` → HTTP 200 (`text/javascript`).
- `GET /dashboard/auth.js` → HTTP 200 (`text/javascript`).
- Unauthenticated `GET /api/discovery/scheduler/status` → HTTP 401, as expected for an admin-only endpoint.
- Dashboard JS syntax: `node --check dashboard/auth.js` and `node --check dashboard/app.js` both passed using the `node:22-alpine` image. The VM's system Node 12.22.9 is not used for this check because the existing dashboard already uses syntax newer than Node 12.

## Initial 10-board scheduled pass

All 10 configured employer boards completed one scheduled initial run. Results from `source_runs` and `ats_board_poll_schedule`:

| Provider | Board | Jobs observed | Requests / outcome |
|---|---|---:|---|
| Ashby | OpenAI | 811 | success |
| Ashby | PostHog | 10 | success |
| Darwinbox | Arvind | 36 | success |
| Greenhouse | Coinbase | 283 | success |
| Greenhouse | Graviton Research Capital | 21 | success |
| Greenhouse | Zocdoc | 64 | success |
| Keka | Bridgestone | 109 | success |
| SmartRecruiters | Bosch Group | 300 | success |
| Workable | Hugging Face | 6 | success |
| Workday | NVIDIA | 20 | success |
| **Total** | **10 boards / 8 providers** | **1,660** | **10/10 success** |

Aggregate first-pass telemetry:

- 10 source-run records; 10/10 board outcomes `success`.
- 53 requests; 53 HTTP 2xx; HTTP 429 = 0; request exceptions = 0.
- Page failures = 0; board failures = 0; successful/attempted boards = 10/10.
- Jobs table = 1,660; notification-ledger rows = 1,660; sent notifications = 0.
- `PRAGMA integrity_check` = `ok`.
- All 10 board `baseline_pending` flags cleared after their successful first polls.
- Seven host rows; no active/expired host leases remained after the run.
- All seven API-host groups and provider boards were staggered/serialized by the scheduler; observed wall-clock initial pass began at 18:27:43 UTC and finished at 18:29:39 UTC.

Workday returned its current freshness-page sample and logged a 2,000-result cap with 15 facet partitions queued. This is correctly represented as incomplete inventory work; this smoke test does **not** claim full NVIDIA inventory coverage.

## Remaining human/browser QA

The candidate has no test user accounts yet. The owner should create an admin and member through the out-of-band CLI (password prompts are interactive; do not place passwords into chat or shell history):

```bash
sudo docker exec -it job-radar-board-scheduler-qa python -m v2.auth_admin create-admin --email qa-admin@jobbeeper.test
sudo docker exec -it job-radar-board-scheduler-qa python -m v2.auth_admin create-user --email qa-member@jobbeeper.test
```

Then complete the separate Desktop browser QA prompt: admin view of all 10 board rows and 7 host rows; member/anonymous denial; due times/outcomes/baselines; refresh; console/network checks; 1440, 1024, 768, 390 and 320 pixel widths. Do not change board activation, notifications, source config, or user preferences during the read-only visual pass. The Desktop report is still pending.

## Exact-head continuation verification — 2026-11-10 09:28 IST

The candidate image was rebuilt from feature commit `06a2ca472c4cc8368b27c4c8ee4a86aa91a6eb1e` and the existing isolated candidate container was recreated against the same dedicated QA volume. The resulting image digest is `sha256:339bd42f54e3f51beedba1a576a55861f992f381d89a54e261505aa5c1b6429c`. Database verification after restart retained 1,660 jobs, 10 source runs, 10/10 successful board schedules, zero pending baselines, zero sent notifications and `PRAGMA integrity_check=ok`.

GitHub Actions V2 CI run #1444 (`42676092793`) passed on the exact head. The workflow log states `Ran 466 tests in 60.421s` and `OK`; the syntax job, Python compile, dashboard JS syntax, focused router/extractor tests and full V2 unittest suite all completed successfully.

Desktop visual/accessibility/browser QA remains pending because this isolated candidate still has no QA users.
