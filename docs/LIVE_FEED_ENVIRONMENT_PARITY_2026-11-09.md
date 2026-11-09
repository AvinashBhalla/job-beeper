# JobBeeper live-feed parity and environment promotion runbook

**Updated:** 2026-11-09 21:15 IST
**Candidate:** PR [#65](https://github.com/AvinashBhalla/job-beeper/pull/65), head `243da9c35e93979e59d0de281130581cad4124d1`
**CI:** V2 run #1437 (`42648073320`) passed all stages, including dashboard JS syntax and full V2 suite.
**Production boundary:** production stays untouched until a separate release approval.

## 1. What is complete in this feature branch

- Optional default-off Hirebase sampler with estimate-first quota guard, persisted local usage ledger and 429 cooldown. No key was supplied and no Hirebase request was made.
- LastRound AI CC BY 4.0 ATS directory imported as low-confidence candidates only.
- Workday incremental inventory cursor and admin status; Workday 2,000-result facet partition queue is persisted, sequential and bounded (depth 4, queue 500, one extra page per board per 15 minutes). Incomplete leaves remain visible.
- Keka default and non-default careers portal resolver, tenant:portal identity and portal-specific collector/verification.
- Unmatched global ATS candidate staging table and admin-only import/list/link/reject APIs for Workday/Keka/Darwinbox. Import creates no employer or board rows. Linking requires an existing employer and creates/reuses a discovered board only; verification and activation remain separate.
- Admin Coverage & Health UI shows board candidates, source coverage and Workday partition progress.
- Open-source/provider research and Common Crawl constraints documented.
- Candidate staging API suite: 11 focused tests passed. Full V2 suite: 451 tests passed in the completed local run. Exact-head GitHub V2 CI #1437 passed all stages. A duplicate final local run is still in progress; CI #1437 is the authoritative completed full-suite result.

## 2. Current environments — verified 2026-11-09

| Environment | Address/container | Code/config | Live feed / data state | Notifications / credentials |
|---|---|---|---|---|
| Production | port 8000, `v2-radar-1` | image `job-radar-prod-canary:6e5becb`; runtime config v15 | 9 active source integrations; DB 23,193 jobs / 25,965 source runs / 1 user | Notifications enabled; production Telegram credentials present. Do not touch. |
| Shared dev | port 8001, `job-radar-dev` | image `job-radar-dev-multitenant:e6181d9`; config v12 | Naukri only scheduled; DB 9,748 jobs / 8,194 source runs / 1 user | Notifications off; Telegram env vars empty; LLM flags false. |
| Connector QA | port 8010, `job-radar-connectors-qa` | old image built from `/tmp/job-radar-next`; config v15 | All sources off; DB empty (0 jobs, 0 runs, 0 users) | Notifications off; Telegram/LLM credentials empty. Current compose has `JOB_BEEPER_FEATURE_DEMO=true`; candidate live-feed compose must set it false. |
| Browser QA | port 8006, `job-radar-browser-qa` | image `job-radar-dev-multitenant:e6181d9`; config v12 | Synthetic role-testing corpus: 4 demo jobs, 2 QA users, 0 source runs | Collectors off; notifications and external credentials off. Keep this isolated synthetic QA instance unchanged. |

All four databases currently pass SQLite `integrity_check=ok`. They are separate volumes/paths. Do not copy production DB, users, preferences, Telegram settings, sessions, notification ledgers or credentials into either non-production environment.

## 3. Production source set and observed request pressure

Effective production config v15 currently enables LinkedIn, Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka and Darwinbox. Instahyre and Lever are off. Public employer-board allowlists: Greenhouse 3, Ashby 2, Workday 1, SmartRecruiters 1, Workable 1, Keka 1, Darwinbox 1; Naukri uses its relay.

Observed source-run aggregates from the prior 24 hours (2026-11-08/09 UTC):

| Source | Runs | New jobs | Requests | 429 | Page failures |
|---|---:|---:|---:|---:|---:|
| LinkedIn | 156 | 200 | 362 | 10 | 7 |
| Naukri | 478 | 376 | 295 | 0 | 0 |
| Greenhouse | 257 | 370 | 771 | 0 | 0 |
| Ashby | 254 | 831 | 508 | 0 | 0 |
| Workday | 626 | 47 | 13,126 | 0 | 1 |
| SmartRecruiters | 255 | 405 | 5,843 | 0 | 1 |
| Workable | 630 | 6 | 630 | 0 | 0 |
| Keka | 629 | 109 | 1,258 | 0 | 0 |
| Darwinbox | 627 | 36 | 627 | 0 | 0 |

LinkedIn is deliberately excluded from newly enabled non-production polling. Ten 429s and seven failed pages in the production sample make duplicating that traffic in two more environments an avoidable risk. LinkedIn remains production-only until its cooldown/rate-limit behaviour is resolved; do not force retries.

## 4. Desired feed-parity model

“Same live feed” means **same real public source adapters and the same employer board allowlist**, each environment collecting into its own database. It does not mean sharing the production DB or credentials, nor identical poll frequency. Non-production polls are slower and staggered so the same postings arrive with a bounded delay while avoiding a 3× request burst.

### Planned source scope

- Enable in dev and connector QA: Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka and Darwinbox, with the same production board URL/slug allowlists.
- Keep disabled in both: LinkedIn (429 exception), Instahyre and Lever (also disabled in production), Hirebase (not a production feed and no key).
- `notifications_enabled=false` in both; blank Telegram bot/chat and webhook credentials; Gemini/LLM flags false; `JOB_BEEPER_FEATURE_DEMO=false` for live-feed QA.
- Keep dev and QA databases, user accounts and preferences separate. Create only synthetic test accounts/preferences in QA.

### Planned cadence

| Source | Production cadence | Shared dev cadence | Connector QA cadence |
|---|---:|---:|---:|
| Naukri | 5 min | 15 min | 60 min |
| Greenhouse | 5 min | 15 min | 60 min |
| Ashby | 5 min | 15 min | 60 min |
| Workday | 2 min | 15 min | 60 min |
| SmartRecruiters | 5 min | 20 min | 60 min |
| Workable | 2 min | 15 min | 60 min |
| Keka | 2 min | 15 min | 60 min |
| Darwinbox | 2 min | 15 min | 60 min |

Based on observed run rates, this adds approximately 17% of production request volume for the two-minute ATS sources, around 33–42% for five-minute sources, and about 42% for Naukri. These are planning estimates from observed run rates, not provider quota guarantees. Watch 429, 5xx, latency and page failures; immediately lengthen the affected non-production cadence if pressure rises.

Feed freshness will not be identical: dev should usually lag production by up to about 15–20 minutes, connector QA by up to about 60 minutes. The same current postings should appear without copying production records. For an immediate connector verification, use one explicit, single-provider QA canary—not an unbounded source-wide scan.

## 5. Promotion order and gates

### Stage A — deploy candidate to shared dev (8001)

1. Confirm PR #65 head `243da9c` and exact-head CI #1437 remain green.
2. Export only the public board allowlist and source flags from production config. Copy only approved board fields (`token/board`, public URL or account identifier, company name); strip all `registry_id` values because IDs are environment-local. Do not copy other production config values.
3. Build immutable image `job-radar-dev-multitenant:243da9c` from the exact candidate checkout.
4. Take a fresh SQLite online backup of the existing dev volume immediately before recreation; record size, SHA-256 and `PRAGMA integrity_check=ok`.
5. Use a new candidate Compose file. Preserve container/project identity, port 8001, existing volume `job-radar-dev_radar-dev-data`, read-only config mount and existing environment behaviour. Never use `down -v`.
6. Apply config v17 with the planned source set/cadence above. Notifications, Telegram, Gemini, LLM and Hirebase remain off.
7. Recreate only `job-radar-dev`. Wait for startup completion; do not restart because an early health probe resets during initial evaluation refresh. Verify health, dashboard, DB integrity, row counts, config flags and zero delivery.
8. Confirm a real successful source run from each of the eight feeds, then at least two scheduler cycles for the active sources. Check jobs seen/new, 2xx/429/5xx, request and page counts, per-user evaluation and feed output; verify zero sends.
9. Owner checks the live dev feed via SSH tunnel. Compare titles/companies/source names and freshness against production, not private user/account state.

### Stage B — deploy the same candidate to connector QA (8010)

1. Proceed only after shared-dev validation is clean. Keep browser QA 8006 on its synthetic fixture corpus; do not overwrite its four demo jobs.
2. Build/reuse the **same exact image SHA** `243da9c` for QA.
3. Take an online backup of the isolated QA volume `job-radar-connectors-qa_qa-data`; it is currently empty, but preserve it.
4. Use a new QA Compose file with loopback port 8010, the QA named volume, QA-only config and blank Telegram/LLM credentials. Set `JOB_BEEPER_FEATURE_DEMO=false` (current QA Compose says true).
5. Apply the same allowlists and source flags as dev, with 60-minute scheduled cadence. Notifications stay off.
6. Create isolated synthetic admin/member accounts and preferences; do not copy dev or production users.
7. Verify all eight feeds with at least one successful live poll each, record per-source metrics, then use QA for provider-specific regression and browser checks.
8. Run two-role browser QA against 8010 with live postings plus synthetic test accounts. Keep the 8006 synthetic baseline available for repeatable role/UI tests.

### Stage C — production release (separate)

Do not promote to production as part of this task. After dev and QA pass, owner reviews the candidate, approves a separate release/merge and production rollout, and we take a fresh production backup. Production port 8000 and its Telegram configuration remain untouched until that separate decision.

## 6. Rollback

- Preserve existing images `job-radar-dev-multitenant:e6181d9` and current QA image tags. Do not overwrite them.
- Keep current live Compose files and volumes. Roll back only the named non-production container to its previous image/config; do not remove volumes.
- Restore DB backups only for confirmed database/schema corruption, not merely an HTTP or UI smoke-check failure.
- Production is not part of this rollback plan because it is not changed.

## 7. Next priorities

**P0:** (1) finish exact final local suite check; (2) deploy candidate to dev and validate real feed/cycles; (3) deploy same image/board allowlist to connector QA and validate all live connectors; (4) resolve LinkedIn 429 separately; (5) implement persistent per-board scheduling/host-level budgets.

**P1:** autonomous Common Crawl CDX and sitemap/career-link candidate discovery; verify/associate candidates; Darwinbox 403/429/5xx classification; source latency/completeness benchmarks; stale/repost and job-legitimacy signals.

**P2:** more ATS connectors, resume vault/answer bank and later application/referral workflows after feed reliability is stable.

## 8. What is needed from the owner

- No credentials are needed to configure public ATS feeds. The current production board allowlist contains public identifiers/URLs, not a production API secret.
- No input is needed to start the dev-first/QA-second rollout requested here.
- For any future LinkedIn non-production feed, a separate decision is required after production 429s settle; do not provide production LinkedIn cookies in chat.
- A dedicated non-production Telegram bot/chat is needed only if you later want to test real notification delivery. It is not needed for feed parity; notifications remain disabled.
- Production deployment requires separate explicit approval after dev/QA UAT.

## Execution results — 2026-11-09 22:09 IST

Candidate SHA `243da9c35e93979e59d0de281130581cad4124d1` is exact-head CI #1437 passed and deployed to dev/QA as immutable image `job-radar-dev-multitenant:243da9c`, SHA `sha256:75d1f8ffe01335f35a7a7447671d2319f46edb4fcfe5eb9cf829617998de5e31`.

- **Dev 8001:** all eight sources completed successful real runs; follow-on cycles show 0 429, 0 page failures, 0 board failures in last two hours. DB 10,259 jobs / 8,221 source runs; integrity ok; zero notification sends.
- **Connector QA 8010:** all eight sources completed first real cycle; 1,864 live jobs, 8 successful runs, 0 429, 0 page failures, 0 board failures. DB integrity ok; zero sends. Next 60-minute full cycle remains to be observed.
- **Browser QA 8006:** unchanged synthetic UI baseline (4 demo jobs, 2 users, collectors off).
- **Production 8000:** unchanged and not restarted.

Backups: dev pre-rollout `/var/backups/job-radar-daily/dev-pre-live-feed-20261109T155300Z.sqlite3` (SHA-256 `cddc7bfbf31f37344a32680c4c2fc238e4c8918715be989c21dadfe56f9d5396`, integrity ok); QA pre-rollout `/var/backups/job-radar-daily/qa-pre-live-feed-20261109T161000Z.sqlite3` (SHA-256 `89724422f7d207aaa24903812638f2ee5a8544ea9a22793dadf543afa931d392`, integrity ok).

Owner testing tunnels: dev `ssh -N -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197` → `http://localhost:18001/dashboard/`; live QA `ssh -N -L 18010:127.0.0.1:8010 ubuntu@130.210.27.197` → `http://localhost:18010/dashboard/`; synthetic QA 8006 remains separate.

Connector QA has no accounts yet. Owner should create QA-only admin/member interactively with `sudo docker exec -it job-radar-connectors-qa python -m v2.auth_admin create-admin --email qa-admin@local.test` then `sudo docker exec -it job-radar-connectors-qa python -m v2.auth_admin create-user --email qa-member@local.test`; passwords are prompted locally and must not be pasted into chat.

PR #65 remains draft/unmerged pending owner UAT. Production is not part of this rollout.

## 2026-11-09 22:19 IST — final QA repeat pass and exact-head docs CI

GitHub Actions V2 CI #1438 / run `42658009285` passed on docs/hand-over commit `b09cba6138035d23f0e413e8a263ff189261f764`. The earlier feature-code commit `243da9c` also passed exact-head CI #1437. PR #65 remains open/draft/unmerged.

A second controlled QA ingestion pass was executed with `radar.run_source()` for all eight enabled providers; source schedule values remained 3,600 seconds and notifications stayed off. Results across two passes per provider:

| Source | Runs | Jobs seen (sum) | New rows (sum) | Requests (sum) | 429 | Page / board failures |
|---|---:|---:|---:|---:|---:|---:|
| Naukri | 2 | 398 | 213 | 2 | 0 | 0 / 0 |
| Greenhouse | 2 | 739 | 370 | 6 | 0 | 0 / 0 |
| Ashby | 2 | 1,648 | 825 | 4 | 0 | 0 / 0 |
| Workday | 2 | 47 | 28 | 43 | 0 | 0 / 0 |
| SmartRecruiters | 2 | 600 | 304 | 46 | 0 | 0 / 0 |
| Workable | 2 | 12 | 6 | 2 | 0 | 0 / 0 |
| Keka | 2 | 218 | 109 | 4 | 0 | 0 / 0 |
| Darwinbox | 2 | 72 | 36 | 2 | 0 | 0 / 0 |

After the second pass QA DB has 1,891 jobs, 16 source runs, 1,891 canonical opportunities, 1,891 global evaluations, 1,891 notification ledger decisions, zero users/preferences, zero sent notifications, and SQLite integrity `ok`. Idempotent feeds returned no new duplicate rows for Ashby, Workable, Keka and Darwinbox; Naukri/Greenhouse/Workday/SmartRecruiters delivered newly available items. The normal 60-minute QA scheduler's next autonomous cycle remains unobserved; the second pass was an explicit controlled test, not a cadence change.

Latest shared dev check: 10,278 jobs, 8,228 source runs, SQLite integrity `ok`, zero sent notifications; health HTTP 200. Production remains untouched.

Only outstanding owner input: create QA-only admin/member interactively with commands documented here, then review admin/member UI on port 8010. Do not copy production credentials/users.
