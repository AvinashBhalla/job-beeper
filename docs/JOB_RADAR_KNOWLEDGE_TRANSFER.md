# Job Radar V2 — Knowledge Transfer

**Snapshot:** 2026-10-09  
**Active release branch:** `v2-live-radar`  
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; older sections may describe superseded states. Use this document and the deployed commit for current status.

## 1. Current state

Latest merged V2 code: `c2f2ce659ad1a6287318ffc1fc1036135577ce4b` — Greenhouse first-publication timestamps and UTC parser fix. Post-merge [V2 CI run #297](https://github.com/AvinashBhalla/job-beeper/actions/runs/37931422233) passed.

Latest VM output supplied 2026-10-09:
- `/health` returned `status=ok`.
- LinkedIn last scan succeeded: 54 seen, 1 new, no error.
- Naukri last scan succeeded: 359 seen, 0 new, no error.
- Greenhouse dry run fetched 298 jobs across 3/3 successful boards. This was a direct collector/matcher preview: no database upsert and no Telegram sends.

### Source configuration

| Source | Enabled | Poll target | Current state |
|---|---:|---:|---|
| LinkedIn | Yes | 60s | Healthy at latest supplied check |
| Naukri | Yes | 300s | Healthy at latest supplied check |
| Instahyre | No | 600s | Not validated for activation |
| Greenhouse | **No** | 900s | Code deployed; awaiting ingestion/dashboard freshness gate |

Runtime config is schema version 7. Greenhouse boards are Coinbase (`coinbase`), Graviton Research Capital (`gravitonresearchcapital`), and Zocdoc (`zocdoc`). Clarifai and Veradigm Asia returned HTTP 404 from their candidate endpoints and were removed.

## 2. Greenhouse findings and current blocker

Latest read-only VM dry run:
- Jobs fetched: 298.
- Publication time: 297 with minute precision, 1 unknown.
- Published in the configured 72-hour window: 10; older: 287; future: 0.
- Profile matches: 1; matches passing current alert policy: 0.
- Only match: Graviton Research Capital, “Software Engineer (2027 Graduate),” Gurugram. Its `first_published` value was `2026-09-01T06:25:41+00:00`, outside the 72-hour window, and its experience requirement was not extracted.
- The corrected location matcher rejected 190 remote postings outside configured location targets.

**Do not enable Greenhouse yet.** The collector fetches the full board. The existing “today” lifecycle is based on discovery time, so importing all 298 board listings may make older postings look newly discovered in the dashboard. Before activation, either add a tested source-posted freshness guard for Greenhouse ingestion or update the UI to clearly separate first-seen time from original posting time. Do not weaken `require_explicit_experience_for_alerts=true) to force alerts.

### Engineering lessons

- `Remote, India` must not act as an unrestricted global `Remote` wildcard. PR #8 fixed this; plain `Remote` intentionally remains global.
- Use `first_published` as the original posting timestamp when present. Never substitute `updated_at`, which may reflect later edits.
- ISO parsing originally lowercased the `Z` timezone suffix, making valid timestamps parse as unknown. The parser now preserves the raw ISO string and handles uppercase/lowercase `Z`; regression tests cover this.
- Runtime preferences persist in the Docker volume at `/data/config.json`. Changing repository defaults in `v2/config.json` does not overwrite that saved VM config. Use the protected config API/dashboard and verify `GET /api/config`.

## 3. Runtime and architecture

- Repo path on VM: `/home/ubuntu/job-beeper`.
- Compose file: `v2/docker-compose.yml`; service: `radar`; usual container: `v2-radar-1`; host port: `8000`.
- Docker volume: `radar-data`; database `/data/jobs.db`; runtime config `/data/config.json`; config token `/data/config_token`.
- Health: `curl -fsS http://127.0.0.1:8000/health`.
- Useful read APIs: `/api/config`, `/api/source-status`, `/api/daily-summary`, `/api/latency-summary?hours=1`.
- Pipeline: source collector → normalize → SQLite upsert → canonical opportunity/deduplication → matching/evaluation → freshness and alertability policy → notification ledger → Telegram.
- The Naukri relay is scheduled in its **separate repository**. The old VM cron that dispatched a private-repo relay workflow was removed. Do not reintroduce it.
- Never print or commit the config token, Telegram secrets, runtime config, private feed, or SQLite database.

## 4. Repositories and branch map

### Repositories
- [Private app repository](https://github.com/AvinashBhalla/job-beeper): current V2 deployment work is in `v2-live-radar`.
- [Separate Naukri relay repository](https://github.com/AvinashBhalla/job-beeper-naukri-relay): active scheduled relay/public feed. It is not the `naukri-relay` branch of the private app repository.

### Branches in the private app repository

| Branch | Purpose and status | Action |
|---|---|---|
| `v2-live-radar` | Active V2 release/deployment branch; latest code merge was `c2f2ce65`. | **Keep.** Branch all V2 work from here and merge tested changes back here. |
| `main` | GitHub default branch, 59 commits behind `v2-live-radar` at this snapshot; its README still describes the older GitHub Actions/static-dashboard design. | **Keep for now; do not deploy V2 from it.** Decide separately whether to promote V2 to main or change the default branch. |
| `feat/greenhouse-first-published-timestamps` | PR #9 merged by squash into `v2-live-radar`. | Stale topic branch; safe to delete. |
| `feat/greenhouse-public-board-source` | PR #6 merged. | Stale topic branch; safe to delete. |
| `fix/naukri-relay-cache-busting` | PR #5 merged. | Stale topic branch; safe to delete. |
| `fix/remote-location-country-qualification` | PR #8 merged. | Stale topic branch; safe to delete. |
| `fix/validate-greenhouse-board-registry` | PR #7 merged. | Stale topic branch; safe to delete. |
| `docs/current-job-radar-knowledge-transfer` | Temporary branch for this knowledge-transfer/README/handover PR #10. | Delete after PR #10 merges. |
| `naukri-relay` | Legacy orphan branch in this private repo containing only `dashboard/data/naukri_relay.json`; no common ancestry with V2. Not the active separate relay repository. | Candidate for deletion after confirming no external automation references this private branch. |

### Merged implementation PRs
- [#5 Naukri relay cache busting](https://github.com/AvinashBhalla/job-beeper/pull/5) — `f91f047c`.
- [#6 Greenhouse public board source](https://github.com/AvinashBhalla/job-beeper/pull/6) — `1cfd55b2`.
- [#7 Validated Greenhouse board registry](https://github.com/AvinashBhalla/job-beeper/pull/7) — `b42193c6`.
- [#8 Country-aware remote matching](https://github.com/AvinashBhalla/job-beeper/pull/8) — `2074bdab`.
- [#9 Greenhouse publication timestamps and ISO parser fix](https://github.com/AvinashBhalla/job-beeper/pull/9) — `c2f2ce65`.

No open PRs were present in the last inventory. The topic branches remain because squash merges do not delete their source branch refs. The current GitHub integration cannot delete refs directly; prune those refs using authenticated Git/GitHub CLI after this documentation change is merged. Keep `main` and `v2-live-radar`.

## 5. Blockers and next pipeline tasks

### P0 — Fix ingestion/dashboard freshness semantics, then trial Greenhouse
1. Ensure stale first-published Greenhouse jobs are not presented as newly posted merely because they were discovered today. Choose a source-level freshness guard or an explicit UI distinction between first-seen and first-published time.
2. Add tests that stale board listings do not appear as fresh and do not queue notification-ledger entries.
3. Confirm Greenhouse stays disabled until the above lands.
4. After CI passes, enable only for a controlled trial. Observe at least one 15-minute cycle, then check source status, logs, inserted rows, recent matches, alertability, and notification ledger.

### P1 — Protect LinkedIn/Naukri reliability
1. Observe several consecutive LinkedIn scans: request counts, 429/failures, duration and useful new jobs. Do not increase concurrency based on a short clean sample.
2. Verify the public Naukri relay keeps refreshing and date-only Naukri postings never claim exact discovery latency.
3. Test Telegram end-to-end on a genuinely fresh and eligible posting; confirm one alert per canonical opportunity.

### P2 — Branch/release hygiene
1. Remove the five merged feature branches and the temporary documentation branch listed above. Remove the private `naukri-relay` branch only after confirming there are no consumers.
2. Decide deliberately what to do with `main`. Until then, production work and deployments must explicitly target `v2-live-radar`.
3. After each release, record the merge SHA, deployed SHA, HTTP health result, runtime config and source-status evidence here.

### P3 — Add sources only after current flow is stable
Evaluate Lever and Ashby next, one at a time. Each must have its own opt-in flag, verified public board, source ID, timestamp precision, dedupe tests, per-board failure isolation, and alert-safety validation.

## 6. Release checklist

Before merge: topic branch cut from current `v2-live-radar`; regression tests added; V2 CI green.

After deployment: verify branch/SHA; Docker service up; `/health` HTTP 200; runtime config/source flags; source-status/logs; no stale or mismatched job alerts; update this handover only with evidence from actual output.
