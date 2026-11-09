# JobBeeper repository cleanup and next-agent handover

**Audit date:** 2026-11-09
**Repository:** `AvinashBhalla/job-beeper`
**Integration branch:** `v2-live-radar`
**Purpose:** reduce branch/PR clutter without discarding active work, deployment history, or owner data.

## Executive result

- Remote branches reduced from **20 to 16**. Four superseded documentation branches were archived as annotated tags before their remote branch names were deleted.
- Open PRs reduced from **8 to 7**. Stale release placeholder PR **#35 was closed unmerged** because GitHub reported it dirty/conflicted (688 commits, 94 files). `main` and `v2-live-radar` were not modified.
- Seven open PRs #59–#65 remain, each for a distinct feature or documentation change and each with a successful exact-head V2 CI run at the audited head. They remain drafts pending owner UAT/review; do not merge them as a batch.
- Two clean inactive local worktrees were removed (`/tmp/job-radar-lever-adapter`, `/tmp/job-radar-pr46-integration`). The corresponding branch refs were retained. `/tmp/job-radar-next` was removed after verifying its QA runbook is byte-identical to the copy on PR #65.
- `/tmp/job-radar-user-preferences` was clean but the worktree removal command returned `Permission denied`; it was left untouched. No branch, data or files from that worktree were deleted.
- Local checkout `/home/ubuntu/job-beeper-dev`, dirty source-observability worktree, deployment/rollback branches, Docker volumes, backups and all runtime containers were preserved.

## PR inventory and disposition

| PR | Branch | Status | Why it remains / was closed | Exact-head CI at audit |
|---|---|---|---|---|
| [#35 V2 → main release placeholder](https://github.com/AvinashBhalla/job-beeper/pull/35) | `v2-live-radar` | **Closed, unmerged** | 688 commits / 94 files; `mergeable_state=dirty`. Not a safe release candidate. A fresh promotion PR must be created only after owner UAT and separate release approval. | Not applicable to closure; historical checks are not a promotion gate. |
| [#65 guarded global ATS discovery](https://github.com/AvinashBhalla/job-beeper/pull/65) | `feat/global-ats-discovery-hirebase-guard-20261109` | Open, draft | Global discovery, candidate staging, guarded Hirebase sampler, Workday facet queue, Keka portal support and coverage work. Main current engineering candidate. | V2 CI #1440, run `42659951412`, passed on `f1651d74d6a64200434b1071209ba08b73aa4e28`. Earlier code/docs checkpoints #1437 and #1438 also passed. |
| [#64 Breezy public connector](https://github.com/AvinashBhalla/job-beeper/pull/64) | `feat/breezy-public-json-20261109` | Open, draft | Default-off connector; endpoint observed but undocumented; board-by-board verification remains required. | #1425 / `42598944361`, passed on `43e288e3f72a2c91b9e109ffd3c42f0f44d6f0ce`. |
| [#63 Coverage & Health UI](https://github.com/AvinashBhalla/job-beeper/pull/63) | `feat/source-health-coverage-ux-20261109` | Open, draft | Separate admin UI improvement; authenticated browser QA still required. | #1424 / `42598601006`, passed on `5d214e4d5e7744aa4769241a2132d8ade75e0563`. |
| [#62 global discovery priorities/docs](https://github.com/AvinashBhalla/job-beeper/pull/62) | `docs/global-ats-discovery-priorities-20261109` | Open, draft | Distinct architecture and priority decisions; not identical to implementation PR #65. | #1423 / `42598578135`, passed on `004d0185f0a6f728d0ef6a5cb1cdf170f703a1e0`. |
| [#61 Teamtailor RSS connector](https://github.com/AvinashBhalla/job-beeper/pull/61) | `feat/teamtailor-public-rss-20261109` | Open, draft | Default-off connector; example feed parsed, populated employer board and repeat-poll proof remain gates. | #1419 / `42586434061`, passed on `f3cdeab11acb599909db115623d3afc8528673c2`. |
| [#60 Personio XML connector](https://github.com/AvinashBhalla/job-beeper/pull/60) | `feat/personio-public-feed-20261109` | Open, draft | Default-off connector; docs tenant had zero positions, so a populated employer tenant is still needed. | #1418 / `42583478160`, passed on `16668504bee6a91f33ad69c71c71d0046b37cda2`. |
| [#59 Recruitee XML connector](https://github.com/AvinashBhalla/job-beeper/pull/59) | `feat/recruitee-public-feed-20261109` | Open, draft | Separate default-off connector, with its own parser/tests and board verification gates. | #1417 / `42583473787`, passed on `039be0f08f2b4233925cd0461207e5c1d4ab92b`. |

**Merge policy:** these seven PRs share files such as `v2/config.json`, `v2/radar.py`, `v2/board_discovery.py` and dashboard modules. Do not merge them together or rebase them all in parallel without a migration/config sequencing plan. Integrate one coherent PR at a time onto the latest `v2-live-radar`, resolve config-version collisions, run exact-head CI, and validate in dev/QA. CI green alone does not mean the feature is accepted or production-ready.

## Branches removed — exact history retained

Each original tip is retained by an annotated remote tag under `archive/repository-cleanup-20261109/`:

| Removed remote branch | Exact commit retained | Archive tag | Reason |
|---|---|---|---|
| `chore/dev-first-policy-and-repo-cleanup` | `2cbdcd6bb527c06f3bca0bd6b07a8a52ac765129` | `archive/repository-cleanup-20261109/chore-dev-first-policy` | Release policy file was byte-for-byte identical to PR #65 copy; latest handover supersedes branch. |
| `docs/career-ops-research-20261108` | `763285efa55542f439bbc9303ec2b9b13ff56c9c` | `archive/repository-cleanup-20261109/career-ops-research` | Historical PR #52 already closed; stale large branch against `main`; research findings are preserved in the current reference-research and product docs. |
| `docs/dev-refresh-and-pr-cleanup-20261109` | `fd8eccc78cbe6d0cea78d843034410acf7adbefd` | `archive/repository-cleanup-20261109/dev-refresh-pr-cleanup` | Policy content identical to PR #65; distinct legacy handover snippets were obsolete v9/v10 prompts and are superseded by the current chronological handover. |
| `docs/two-role-browser-qa-20261109` | `c445b178769dc39d2f7c3985a9e48097526e99dc` | `archive/repository-cleanup-20261109/two-role-browser-qa` | `docs/QA/DESKTOP_TWO_ROLE_QA_2026-11-09.md` has the same blob SHA `a55034d3be8a33efbfb32d06ceefc4d38b90b4ef` on PR #65. |

All four remote tags were pushed and verified with `git ls-remote --tags`; their peeled `^{}` commits match the original branch tips. The corresponding remote branch deletion completed successfully.

## Remaining remote branch inventory

These 16 refs were verified after cleanup:

- Integration/release roots: `main`, `v2-live-radar`.
- Active PR heads: `feat/global-ats-discovery-hirebase-guard-20261109`, `feat/breezy-public-json-20261109`, `feat/source-health-coverage-ux-20261109`, `docs/global-ats-discovery-priorities-20261109`, `feat/teamtailor-public-rss-20261109`, `feat/personio-public-feed-20261109`, `feat/recruitee-public-feed-20261109`.
- Preserved branches pending code-equivalence or recovery audit: `feat/admin-board-disable-20261108`, `feat/lever-source-adapter-20261108`, `feat/server-application-tracker-20261109`, `feat/user-preferences-evaluations-20261106`, `fix/board-baseline-pending-20261108`, `fix/sqlite-notification-contention-20261108`, `integration/pr46-v2-rebase-20261108`.

Do not delete the seven preserved non-PR65 refs based only on their PRs being closed or their commit ancestry being divergent. Their diffs include possible unique notification-baseline, board-disable, application-tracker, preferences, Lever and SQLite contention changes. First compare exact functions/tests/docs against current V2, record equivalence, and preserve an archive tag before any deletion. In particular, keep the SQLite P0 recovery lineage and the board-baseline notification-safety fix until explicitly reconciled.

## Local worktree and recovery inventory

- Before this cleanup there were 16 linked worktrees; after removing `/tmp/job-radar-next`, `/tmp/job-radar-lever-adapter` and `/tmp/job-radar-pr46-integration`, there are **13**. The preferences worktree remains because the filesystem refused its removal; no force-delete was attempted.
- `/home/ubuntu/job-beeper-dev` remains dirty and 94 commits behind the remote V2 integration branch. Preserve `v2/config.json`, `.env.save`, `.venv/` and `v2/config.json.backup.20261105-183321`; do not pull/reset/clean/stage it.
- `/tmp/job-radar-source-observability` remains dirty; preserve it and inspect its diff before reuse.
- Deployment/rollback worktrees and branches (`prod-canary-7b1a80d`, detached SQLite-fix worktree, production release/hotfix refs), the local-only HTTPS handoff refs, and `job-radar-user-preferences` port 8002 experiment were not touched.
- The active candidate source worktree is `/tmp/job-radar-global-discovery`; its PR branch head at audit was `f1651d74d6a64200434b1071209ba08b73aa4e28`.

## Runtime parity and QA evidence (no runtime changes in this cleanup)

- Shared dev `job-radar-dev` on loopback port 8001 and connector QA `job-radar-connectors-qa` on loopback port 8010 both run `job-radar-dev-multitenant:243da9c`, image SHA `sha256:75d1f8ffe01335f35a7a7447671d2319f46edb4fcfe5eb9cf829617998de5e31`, restart count 0. Health endpoints returned HTTP 200.
- Eight real feeds are configured for non-production verification: Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka and Darwinbox. LinkedIn remains disabled outside production because of the production 429 history; Instahyre, Lever and Hirebase remain off in these environments.
- Latest controlled QA pass: two `run_source()` passes per provider, 16 successful source runs, 1,891 unique jobs, zero HTTP 429, zero page failures, zero board failures, SQLite integrity `ok`, and zero notification sends. The manually-triggered second pass is not evidence that the autonomous 60-minute QA scheduler has completed its next cycle.
- Latest dev checkpoint: 10,278 jobs, 8,228 source runs, SQLite integrity `ok`, and zero sent notifications. Dev notifications/Telegram, Gemini and LLM credentials/routing remain disabled/blank.
- Synthetic browser QA on port 8006 remains a separate fixture environment (four demo jobs, two existing test accounts, collectors off); do not overwrite it with live data.
- Production container `v2-radar-1` remains on `job-radar-prod-canary:6e5becb`, image SHA `sha256:6786502548d98fbc5d92d4d2670bd20022acaa0c5f70e940f7020bd24d72a9c5`, restart count 0. It was not restarted, reconfigured, migrated or otherwise modified in this cleanup.

### Owner QA access

- Dev tunnel: `ssh -N -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197` → `http://localhost:18001/dashboard/`.
- Live connector QA tunnel: `ssh -N -L 18010:127.0.0.1:8010 ubuntu@130.210.27.197` → `http://localhost:18010/dashboard/`.
- Synthetic browser QA tunnel: `ssh -N -L 18006:127.0.0.1:8006 ubuntu@130.210.27.197` → `http://localhost:18006/dashboard/`.
- Connector QA currently has no users. Owner must create QA-only admin/member interactively, with passwords entered locally (never sent to chat):

  ```bash
  sudo docker exec -it job-radar-connectors-qa python -m v2.auth_admin create-admin --email qa-admin@local.test
  sudo docker exec -it job-radar-connectors-qa python -m v2.auth_admin create-user --email qa-member@local.test
  ```

## Next-agent execution plan

### P0 — close the current QA loop

1. Read `docs/RECOVERY_CHECKPOINT_2026-11-09_2209_IST.md`, `docs/LIVE_FEED_ENVIRONMENT_PARITY_2026-11-09.md` and `docs/QA/DESKTOP_TWO_ROLE_QA_2026-11-09.md` before acting.
2. Ask the owner to provision isolated QA admin/member accounts as above; perform role-based UAT on 8010. Verify member/admin route permissions, Coverage & Health, live feed, filters, and tenant separation. Keep passwords, cookies and tokens out of notes/screenshots.
3. Observe the next autonomous 60-minute QA source cycle; record each provider's run time, jobs seen/new, request/page/board counts, status codes, 429/backoff, and DB integrity. Do not describe a manual rerun as scheduler evidence.
4. Owner reviews dev 8001 and connector QA 8010 live feeds; record discrepancies with exact steps, timestamp and sanitized evidence. Keep notifications disabled.
5. Review PR #65 diff and owner acceptance. Keep it draft/unmerged until UAT and review gates pass. Current CI #1440 is green only for the audited feature head; a subsequent docs commit must have its own exact-head CI result.

### P1 — source completeness and operational reliability

6. Implement the persistent per-board scheduler: `next_due_at`, per-host/provider concurrency budgets, jitter, Retry-After handling, persisted cooldown, cursor/checkpoint state, backpressure and queue age/unfinished-board visibility. Avoid global concurrency knobs that ignore provider limits.
7. Implement Common Crawl CDX and sitemap/career-link harvesters as slow candidate-discovery inputs only. Serialize CDX requests; stop and apply a 24-hour cooldown after 503/IP block; no proxy rotation or parallel sweeps. Candidates must retain provenance, be live-verified and linked to an existing employer before activation.
8. Preserve Darwinbox 403/429/5xx classification; 403 remains blocked. No Cloudflare/TLS fingerprint bypass.
9. Benchmark p50/p95 request and full-board latency, first-seen delay, completeness, duplicate/repost rate and retry/cooldown behaviour. Track Workday facet queue progress/incomplete leaves.
10. Reconcile preserved branches with exact path/function/test comparisons. Archive refs first; delete only fully superseded branches/worktrees. Sequence active PR merges with config migrations, one PR at a time.

### P2 — product workflow

11. Posting legitimacy, stale/closed/repost checks and explainable evidence-weighted fit.
12. Per-user resume vault/versioning and answer bank with provenance and approval for inferred facts.
13. Later: approval-gated browser form fill, referral research and application follow-up. No unattended application submission or message sending.

## Non-negotiable safety boundary

- All engineering goes to feature branches from the latest `v2-live-radar`, then exact-head CI, isolated dev/QA, owner UAT and a separate explicit production approval.
- Never deploy, restart, alter config, change source flags, touch DBs, send test Telegram messages or run migrations on production as part of this task.
- Preserve existing volumes, backups, owner-local files, and rollback images. No destructive `git clean`, `reset --hard`, force-push, branch deletion or container recreation without a documented equivalence/backup gate.
