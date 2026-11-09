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
