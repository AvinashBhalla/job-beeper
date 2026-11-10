# JobBeeper development-first release policy and repository cleanup

**Owner decision:** 2026-11-09. Production is for owner UAT only. All engineering changes must be developed and verified outside production first.

## 1. Non-negotiable environment boundary

| Environment | Purpose | Current known endpoint/runtime | Allowed work |
|---|---|---|---|
| Production | Owner's live UAT and stable service | `https://130.210.27.197/`; Nginx 443 → loopback app 8000; image `job-radar-prod-canary:6e5becb` at last check | Read-only diagnosis and owner-authorized release/rollback only. No feature edits, test sends, config experiments or direct migrations. |
| Shared development | Integration/UAT before release | VM loopback 8001 (`job-radar-dev`), health last observed 200; last recorded image `job-radar-dev-multitenant:c441737` | Candidate deploys only after CI, backup, config review and explicit dev-only rollout. Notifications must stay off; never use production Telegram destination. |
| Connector QA | Isolated source integration verification | Loopback 8010 (`job-radar-connectors-qa`) | Controlled source tests, synthetic/disposable data, no production credentials/delivery. |
| Feature sandboxes | Isolated feature experiments | Ports 8002 and 8004 were previously recorded | Use only after verifying process, DB and env isolation; no shared/prod volume or prod secrets. |

**Important freshness caveat:** the Git checkout `/home/ubuntu/job-beeper-dev` is not a clean source of truth: branch `v2-live-radar` was at `7ebc38b`, behind the remote integration head, and had owner/VM-local modifications (`v2/config.json`, `.env.save`, `.venv/`, config backup). Do not pull, reset, clean, overwrite, stage or delete these. The shared-dev container was separately running image `c441737`; do not assume the checkout, container image and remote branch are identical. Before the next dev release, reconcile them using a separate clean worktree and inspect the live compose/env/volume identity. Preserve all existing dev data.

## 2. Required delivery path

1. Start each task from the latest `origin/v2-live-radar` in a clean worktree.
2. Create one short-lived branch per coherent feature/fix. Do not develop on `main`, `v2-live-radar`, or the production checkout.
3. Apply Ponytail/code-simplification review only after understanding the code and its tests. Preserve behavior; no line-count-only refactors. Keep refactors separate from feature changes.
4. Run targeted tests, full `python -m unittest discover -s v2 -p 'test_*.py' -v`, Python compile checks, dashboard JS syntax (`node --check dashboard/auth.js && node --check dashboard/app.js`), JSON validation and `git diff --check` as applicable.
5. Push branch and open PR targeting `v2-live-radar`. Require exact-head GitHub Actions CI green. Review security, tenant isolation, source rate limits, baseline/no-backlog behavior, SQLite locking and rollback implications.
6. Only then deploy to shared dev (8001 or the explicitly selected isolated QA instance), with a fresh online SQLite backup, verified config and preserved volume. Confirm candidate image SHA, health, DB integrity, connector flags and notification-off state. Exercise real sources in bounded mode and observe at least two poll cycles where relevant.
7. Owner performs UAT. Record each bug with steps, expected/actual behavior, screenshots/log timestamps and affected source/user. Reproduce/fix on a new dev branch; never patch production directly.
8. Promote only after owner approves the candidate. Use a separate release PR/change, pre-deploy backup, exact image SHA, migration/rollback plan and post-deploy smoke/soak checks. Do not auto-merge or deploy from this policy alone.

### Release gates

- [ ] Exact candidate commit has passing CI.
- [ ] Diff reviewed; no secrets, local state, data files or unrelated changes.
- [ ] Database backup completed using SQLite online backup API; backup integrity and SHA-256 recorded.
- [ ] Existing volume, config and environment preserved; no destructive migration without tested rollback.
- [ ] Shared-dev image is built from the exact commit and reported in deployment notes.
- [ ] Health/API/dashboard and `PRAGMA integrity_check` pass.
- [ ] Source-specific request/page/board metrics and latency observed; rate limits respected.
- [ ] No test notification can reach a production chat; delivery tests use a dedicated dev bot/chat and explicit opt-in.
- [ ] Owner UAT accepted; production approval is explicit and separate.

## 3. Career-Ops and extension adoption decision

Do **not** reverse engineer private internals or replace JobBeeper's architecture. Use publicly available source and documentation to understand observable product behavior, and inspect the two reference repositories as engineering references. Adopt ideas and independently implement them; do not copy substantial code without license/dependency review and attribution.

### Adopt in planned order

| Pattern | JobBeeper implementation direction | Priority |
|---|---|---|
| Posting legitimacy/repost/open-state revalidation | Recheck original employer/ATS posting before application prep; persist observations and distinguish closed, stale and reposted | P1 |
| Evidence-weighted fit | Hard eligibility blockers plus explainable weighted evidence; provenance for JD facts vs inference; calibrated confidence and user override | P1 |
| Truthful tailored CV and cover letter | Per-user source resume/fact vault, job-specific version history, ATS-safe output; every claim grounded in user-confirmed facts | P1 after resume vault |
| Reusable application answer bank | Per-user canonical question intent, answer, source, confidence, confirmation date, usage/correction history; inferred answers pending approval | P1 |
| Referral/contact discovery | Research hiring managers/recruiters/peers with evidence and confidence; draft outreach only, user approves sending | P2 |
| Browser-assisted form filling | Optional companion after stable application/answer-bank APIs; fill supported fields, show snapshot and stop before submit | P2 |
| Outcome learning | Track applications/interviews/rejections and improve search/matching with user consent | P2 |

### Do not adopt blindly

- Do not port Career-Ops local-first CLI/file runtime into the hosted multi-user FastAPI product.
- Do not make unofficial LinkedIn DOM scraping, Kimi Webbridge or fragile selectors a core dependency.
- Do not automatically send referral messages or submit applications.
- Do not fabricate resume facts, answers, experience or timestamps.
- Do not implement marketing claims (for example a fixed six-hour delay) without independently observed evidence and a clear product requirement.

### Target product workflow

Shared source discovery → canonical dedupe → per-user evaluation → job legitimacy/freshness check → tailored resume and answer preparation → optional browser-assisted form fill → user review and submission → application tracking → referral research and approved follow-up.

The existing shared ingestion engine remains shared; resumes, answer banks, evaluations, applications, contacts and notification destinations remain tenant-owned. The deterministic matcher remains authoritative until LLM improvements demonstrate measured lift.

## 4. GitHub PR audit — 2026-11-09

Only four open PRs were observed in `AvinashBhalla/job-beeper` at audit time:

| PR | Current role | Finding / action |
|---|---|---|
| #35 — V2 to main release gate | `v2-live-radar` → `main`, draft | Keep open and draft. GitHub reports dirty/diverged. It is a release-gate placeholder, not merge-ready. Reconcile `main` only as a separately planned release. |
| #46 — per-user preferences | feature branch → `v2-live-radar`, draft | Feature family is now present in current V2, including per-user preferences, Telegram API and application tracker. Branch is stale/conflicted and its tree would remove newer code/docs. Verify the latest preference-save fix is present in current V2 (dashboard contract and API regression tests are present), then close as superseded; preserve branch until code-equivalence review is archived. |
| #50 — Lever source | feature branch → `v2-live-radar`, draft | Lever adapter, tests, config migration and baseline guard are already present in current V2; Lever remains default-off with empty allowlist. PR branch is stale and merging it would remove newer V2 functionality. Close as superseded after retaining source research and adapter history in current docs. |
| #52 — Career-Ops research | docs branch → `main`, draft | Unsafe/stale base: 89-file / 28,707-addition PR against `main`; compared with current V2 tree it removes newer application-tracker code and the living product roadmap, among other differences. Do not merge. Research is already captured in `REFERENCE_REPOSITORIES_RESEARCH_2026-11-08.md`, `PRODUCT_VISION_AND_DELIVERY_ROADMAP.md` and reverse-engineering notes. Close as superseded. |

At the audit, PR #35 CI syntax check passed. PR #50 syntax check passed for its then-current head; PR #46/#52 showed no checks. Passing an older branch check does not validate a new candidate.

**Cleanup rule:** close only PRs whose feature/documentation is represented in current V2 and whose unique fixes have been verified. Do not mass-delete branches, worktrees, tags or historical docs. First archive exact head SHA and confirm all useful code/tests/docs are present in the current integration branch. Then delete only fully superseded remote/local branches and unused worktrees. Never delete `main`, `v2-live-radar`, production deployment artifacts, public Naukri relay repo/branch, data volumes, backups or local owner state.

## 5. Current engineering priorities after owner UAT

1. Owner manually verifies production login, job feed, filters, board controls and Telegram test receipt. Production remains unchanged while feedback is collected.
2. Reconcile dev source checkout/runtime/image safely; establish one authoritative clean dev worktree and a repeatable deploy script/runbook.
3. Improve notification quality: explain why eligible jobs are queued/suppressed; verify profile evaluation freshness and admin-vs-member Telegram ownership; build dedicated dev Telegram E2E without production destination.
4. LinkedIn: respect persisted 429 cooldown, inspect response headers and pacing; do not force retry or claim healthy until a paced live run succeeds.
5. ATS coverage: continue employer-board discovery and verified allowlist. Workday and Darwinbox are already in the configured connector set in current prod; expand other providers only with bounded endpoint probes, provider-specific parser/tests and default-off activation.
6. Product intelligence: posting legitimacy/repost check and explainable fit before resume tailoring.
7. Application foundation: server-owned applications (already released), resume vault/versioning, answer bank, then browser-assisted application flow.
8. Referrals and follow-ups with source provenance and user approval.

## 6. Owner feedback protocol

When the owner reports a bug, capture: page/route, account role (never password), source/provider, exact steps, expected result, actual result, approximate local timestamp, screenshot/console/network response with tokens/cookies redacted. Reproduce against dev data first. Do not ask for passwords or paste secrets into chat.

## 7. Documentation source of truth

- Product direction and priority: `docs/PRODUCT_VISION_AND_DELIVERY_ROADMAP.md`.
- Reference repository findings: `docs/REFERENCE_REPOSITORIES_RESEARCH_2026-11-08.md`.
- Public JobBeeper behavior and unknowns: `docs/PRODUCT_REVERSE_ENGINEERING_2026-11-08.md` and `docs/PRODUCT_REVERSE_ENGINEERING_PLAN.md`.
- Detailed operational history: `docs/JOB_RADAR_HANDOVER.md`.
- Compact next-agent state: `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/NEXT_AGENT_START_HERE.md`.
- This policy supersedes older handover statements that imply direct changes on `v2-live-radar` or production. Feature branches target `v2-live-radar`; shared dev is the first deployment target; production requires owner UAT and explicit approval.

## 8. Executed cleanup and shared-dev refresh — 2026-11-09

### GitHub PR cleanup completed

- Closed PR #46 (superseded preferences branch), #50 (superseded Lever branch) and #52 (stale Career-Ops branch against `main`) with explanatory comments. No code was merged from these PRs.
- PR #35 remains the only open PR and remains draft as the V2→main release gate.
- The documentation policy was merged through PR #56 into `v2-live-radar` (merge commit `e6181d93682d6c09cd462c18b13b20996ce99057`). Exact branch-head CI run `42573822254` passed, including Python compile, dashboard JavaScript syntax, focused router/extractor tests and full V2 unittest suite. The merge commit's push CI run `42573997642` also passed the same checks.
- Branch heads for #46/#50/#52 are intentionally retained temporarily. Their commits are not all ancestors of current V2 because work was integrated/rebased; do not delete branches until a final path-level equivalence/archive review is complete. No mass branch/worktree deletion was performed.

### Shared dev refreshed safely to current V2 integration head

- Clean source worktree: `/tmp/job-radar-dev-refresh`, detached at exact `e6181d93682d6c09cd462c18b13b20996ce99057` (`v2-live-radar`). The dirty `/home/ubuntu/job-beeper-dev` checkout was not modified.
- Fresh online SQLite backup taken before recreation: `/var/backups/job-radar-daily/dev-pre-v2-refresh-20261109T063814Z.sqlite3`; 51,990,528 bytes; SHA-256 `e0f7cbdacd54acba246792dd97f6f1a43f5b772de7ba6e3ba4376c46ddefceb6`; `PRAGMA integrity_check=ok`; counts before deploy: 9,562 jobs, 8,086 source_runs, 1 user, 1 preference row, 9,562 user evaluations, 9,562 global notification rows, 0 member notification rows.
- Existing dev image preserved as `job-radar-dev-multitenant:rollback-c441737-20261109` (original `c441737` tag also retained).
- Built image `job-radar-dev-multitenant:e6181d9`, image ID `sha256:1e57c7ac3acae83f99bbc230f1980bfec14bb52d7c0fa8456526b09a3c8aa651` from that exact source SHA.
- Recreated only `job-radar-dev` on loopback `127.0.0.1:8001`, using the existing external volume `job-radar-dev_radar-dev-data` and a read-only config bind from the clean worktree. A dedicated `/tmp/job-radar-dev-refresh.yml` was used with Telegram credentials blank and Gemini/LLM flags explicitly false; no `.env` secrets were copied into the new container.
- Initial health probe during startup briefly reset while startup evaluation refresh was running. Logs later showed `Application startup complete`; health returned 200. Do not immediately restart a slow-starting dev container: check logs/process and retry health first.
- Post-refresh: container running, restart count 0; `/health` HTTP 200; SQLite WAL mode, integrity `ok`; config version 12; notifications false; only Naukri enabled; Telegram token/chat absent; Gemini extraction/matcher and LLM router/matcher all false.
- Additive application-tracker schema initialized successfully: `user_applications` now exists with 0 rows. Jobs remained 9,562; source_runs 8,087; user/evaluation/notification history preserved. Global and per-user sent counts both 0. Latest Naukri poll succeeded: 293 seen, 0 new.
- Production was not recreated, modified or reconfigured. Production image remains `job-radar-prod-canary:6e5becb`, image ID `sha256:6786502548d98fbc5d92d4d2670bd20022acaa0c5f70e940f7020bd24d72a9c5`, running with restart count 0; HTTPS health returned 200.

### Current boundary

Shared dev now runs the current V2 integration code and is safe for development/UAT of code paths with notifications disabled and Naukri as the only scheduled source. It is not a copy of production config: the dev preset intentionally remains Naukri-only and notification-off. Production continues serving the owner's manual UAT. Any reported production issue must be reproduced against this refreshed dev runtime first.


## 9. Owner-requested repository cleanup — 2026-11-09

This section supersedes the earlier recommendation in §4/§8 to keep PR #35 open as a release placeholder. The owner asked to remove unnecessary PR/branch clutter. PR #35 was closed **unmerged** because it was a 688-commit, 94-file V2→main PR and GitHub reported `mergeable_state=dirty`. This is not authorization to promote; `main`, `v2-live-radar`, production and all runtime data were left unchanged. After owner UAT and explicit separate approval, create a fresh release PR from the then-current V2 integration SHA with exact-head CI, backup, migration/rollback plan and smoke/soak evidence.

Four superseded documentation branches were archived as annotated tags under `archive/repository-cleanup-20261109/` before deleting their remote branch names. Seven independent feature/docs PRs #59–#65 remain open/draft; do not batch-merge them because they overlap config and collector modules. The full branch inventory, exact SHAs, CI evidence, worktree cleanup and QA handoff are in `docs/REPOSITORY_CLEANUP_2026-11-09.md`.
