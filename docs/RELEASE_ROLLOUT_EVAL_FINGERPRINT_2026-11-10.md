# Release rollout — stable evaluation fingerprints (2026-11-10)

## Summary

PR [#69](https://github.com/AvinashBhalla/job-beeper/pull/69) was merged into `v2-live-radar` at `18f219dfab4ad6f2c5ad9b9704da5d3a220f7d37`. The exact merged source tree is deployed to shared Dev and Connector QA.

- Image tag in both environments: `job-radar-dev-multitenant:18f219d`
- Image ID in both: `sha256:86693f94cf64db076ae79222ca4cf6a05a62c0b4b3fa0be0b6b09444077397d5`
- Git remote `origin/v2-live-radar` was verified equal to the merge commit and tree before documentation work.
- Production container `v2-radar-1` on port 8000 was not modified.
- No app config, poll cadence, concurrency, board registry, or notification settings were changed during rollout.

## Environments

| Environment | Container | Local port | Image | Restart count | Health |
|---|---|---:|---|---:|---|
| Dev | `job-radar-dev` | 8001 | `18f219d` | 0 | HTTP 200 |
| Connector QA | `job-radar-connectors-qa` | 8010 | `18f219d` | 0 | HTTP 200 |
| Production | `v2-radar-1` | 8000 | unchanged | not changed | not part of this rollout |

Private Dev dashboard: [Open JobBeeper Dev](https://termal.in/account#open-site=776b26fb-86fa-4ac2-9762-4af7dd5fe33f)

## Backups and rollback

Fresh online SQLite backups and runtime config snapshots were taken before replacing either container. They are retained on the VM at:

`/tmp/job-radar-release-backups/2026-11-10-pre-eval-fingerprint/`

The backup directory includes:
- `job-radar-dev.sqlite3`
- `job-radar-dev-config.json`
- `job-radar-connectors-qa.sqlite3`
- `job-radar-connectors-qa-config.json`
- `SHA256SUMS`

The previous containers are retained stopped under:
- `job-radar-dev-pre-eval-fingerprint-20261110`
- `job-radar-connectors-qa-pre-eval-fingerprint-20261110`

Do not delete these until owner UAT and the next release gate are accepted. Restore requires matching the prior image and DB volume; do not point the new app at an old database without checking schema/config compatibility.

## Post-deploy verification

Observed on 2026-11-10 around 14:43 IST (09:13 UTC):

| Check | Dev | Connector QA |
|---|---:|---:|
| `/health` | HTTP 200 | HTTP 200 |
| Container restarts | 0 | 0 |
| SQLite integrity | `ok` | `ok` |
| Jobs | 10,847 | 2,433 |
| Evaluation rows | 10,847 | 2,433 |
| Fingerprint mismatches | 0 | 0 |
| Active ATS boards | 10 | 10 |
| Latest board outcome counts | 10 success | 10 success |
| Sent notifications | 0 | 0 |
| Anonymous scheduler-status API | HTTP 401 | HTTP 401 |
| Anonymous source-status API | HTTP 401 | HTTP 401 |

Both databases had matching evaluation rows and zero rows whose fingerprint differed from the active matcher/alertability fingerprint. The initial one-time re-evaluation/migration completed without manual refresh. SQLite integrity checks passed.

The active board inventory is 10 boards across 7 ATS providers and 7 host keys:
- Ashby: OpenAI, PostHog
- Darwinbox: Arvind
- Greenhouse: Coinbase, Graviton Research Capital, Zocdoc
- Keka: Bridgestone
- SmartRecruiters: Bosch Group
- Workable: Hugging Face
- Workday: NVIDIA

### Live poll coverage after deployment

Dev has now completed a full natural post-release board cycle: all 10 of 10 active board rows have a last-finished timestamp later than the 08:47:47 UTC rollout and all latest outcomes are success. The Dev database currently has 10,850 jobs and 10,850 evaluations, zero fingerprint mismatches, SQLite integrity ok and zero sent notifications. The 10 boards' next due times have advanced normally; no manual poll was triggered.

Connector QA uses a 60-minute board cadence. At 09:18 UTC, one Naukri relay run had completed after the 08:53:27 UTC rollout, while 0/10 board rows had yet reached their next due time. A follow-up at 09:18 UTC reconfirmed 0/10 post-release QA board rows; their next due times fall between 09:44:56 and 09:52:46 UTC. Continue observing until every QA board has completed one full post-deploy cycle. Do not manually trigger polls to accelerate this.

### Phase timing signal

The fingerprint defect previously caused each board-scoped poll to hash different operational/source configuration and therefore re-evaluate the whole job inventory. After the fix, post-deploy Dev runs show evaluation phases mostly around 0.1–1.4 seconds in the available natural samples. In contrast, pre-fix samples included repeated 40–160 second evaluation phases.

Examples from Dev after rollout:
- Ashby: one recent run evaluation 0.20s; upsert 0.19s. Earlier post-rollout Ashby sample had upsert 16.32s.
- Greenhouse: recent evaluation samples around 0.08–0.32s; upsert varied up to 1.99s.
- Darwinbox: evaluation around 0.12–0.38s; upsert around 0.15–0.20s.
- Naukri: evaluation median in the small post-rollout sample 0.84s; upsert median 2.71s.
- Workday: evaluation around 1.3s; 42 requests over two observed runs.

These are small, early natural samples, not a controlled benchmark or SLA. Upsert duration still varies (Ashby peaked at 16.32s in the early sample). The upsert lookup plan uses the unique jobs(source, source_job_id) index; canonical URL and company/location candidate lookup plans also use indexes, though company/location ordering uses a temporary B-tree. There is no evidence yet of a full table scan on these hot lookup paths. Continue collecting at least 20 successful post-release runs per provider and measure SQLite lock wait before deciding whether an upsert optimization is needed. The current evidence supports the fingerprint fix; it does not yet prove the upsert bottleneck is eliminated.

## Owner browser QA

The server-side release gate is green. Visual/browser acceptance is still pending.

Use the ready-to-paste prompt in [DEV_DESKTOP_QA_PROMPT_2026-11-10.md](DEV_DESKTOP_QA_PROMPT_2026-11-10.md). It limits the session to Dev, read-only navigation, 10-board scheduler visibility, reload persistence, browser console, and the viewport matrix 1440×900, 1024×768, 768×1024, 390×844 and 320×740. It asks Desktop to produce a Markdown report and actual PNG screenshots. The owner enters credentials directly in the browser; never paste passwords into chat.

No visual QA results or screenshots are claimed in this rollout record.

## Next engineering tasks

1. Owner tests Dev UI using the runbook and returns any bugs/report.
2. Dev's full natural post-release board cycle is complete (10/10). Continue QA observation until all 10 QA board timestamps are post-release.
3. Re-audit fingerprint mismatches after subsequent board polls; expected zero.
4. Collect at least 20 successful post-release runs per provider and compare collector, upsert, evaluation and notification phase times. Keep cadence/concurrency unchanged while collecting.
5. If upsert remains the dominant bottleneck, profile the actual SQL/SQLite lock-wait paths first. Add targeted telemetry or a benchmark before changing write strategy. Preserve canonicalization, per-user evaluations, baseline suppression and source metadata semantics.
6. Review Desktop QA screenshots/report and fix any confirmed UI defects on a separate branch with focused tests and exact-head CI.
7. Production promotion requires a separate explicit owner decision and a separate release record.

## Release safety rules

- Dev-first; Connector QA follows the same immutable image.
- No production deployment without explicit owner approval.
- No manual source polls, inventory refreshes or notification tests during read-only QA.
- Keep live public feeds and separate environment databases; never copy Dev/QA user data to production.
- Keep the prior containers and backups until owner acceptance.
