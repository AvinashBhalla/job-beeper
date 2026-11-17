# Company Watch → Job Radar V2 integration: engineering plan and agent handover

**Date:** 2026-11-17  
**Repository:** `AvinashBhalla/job-beeper`  
**Target integration branch:** `v2-live-radar`  
**Planning branch:** `docs/company-watch-v2-integration-handover-20261117`  
**Baseline V2 commit inspected:** `5c28d97ea39edfa8af13d9686f7b97c3997901f3`  
**Status:** Documentation and read-only audit complete. No application code, source configuration, database, scheduler, deployment or notification setting was changed. PR #74 exact-head GitHub V2 CI is red: 484 tests, 10 failures and 2 errors, all in `v2/test_user_notifications.py`; see the CI section below.

> **Primary direction:** Use Company Watch as a curated source-discovery input. Do not run it as a second production job pipeline. Reconcile verified company/board records into the existing V2 directory, then use V2 collectors, JD enrichment, SQLite, canonical dedupe, per-user preferences/evaluations and per-user Telegram delivery.

## 1. Mission and definition of success

The goal is not to increase the number of job records at any cost. It is to increase the number of **genuinely relevant, sufficiently described, fresh and deduplicated opportunities** that reach the existing JobBeeper product.

A successful integration will:

1. Reuse the current V2 provider collectors wherever they already cover the ATS. Avoid porting duplicate provider adapters from `company_watch/scan.py`.
2. Import the Company Watch company/board inventory as reviewable evidence, not as an automatically active allowlist.
3. Resolve company identity and ATS board identity independently. A tenant slug, ATS domain or search URL is not proof of the employer's canonical identity.
4. Fetch/retain a usable job description (JD) before an item from this new source family can be promoted to an automatic alert.
5. Evaluate jobs with the existing V2 deterministic matcher and each user's saved preferences. Do not add another `filters.json`, a second scoring engine or an LLM dependency.
6. Send only through the existing per-user opt-in Telegram delivery system. Company Watch must not call Telegram directly.
7. Preserve board-level baseline suppression, source timestamps, rate-limit controls, canonical deduplication, notification history and explainable rejection reasons.
8. Roll out in shadow mode first, then enable only a small, verified subset after measuring relevance and JD completeness.

### Explicit non-goals for this increment

- Do not add hundreds or thousands of new company records.
- Do not change the current user preference values or silently copy Company Watch's hardcoded filters into user profiles.
- Do not alter existing LinkedIn, Naukri or other source alert behaviour globally.
- Do not enable Telegram, activate boards, change poll cadences or deploy to production as part of the documentation/planning task.
- Do not use proxies, CAPTCHA workarounds, TLS impersonation, alternate identities or other access-control bypasses.
- Do not replace the existing ATS directory, scheduler or notification pipeline.

## 2. Repository and branch map — critical before starting

The work exists on two different branches and those branches must not be confused.

| Location | Current state | Correct use |
|---|---|---|
| `main` | Company Watch PR #72 merged. Current head inspected: `29cbb17190b26829d49e1458137d75f2e8f286aa`. | Contains the standalone Company Watch prototype and an older V2 lineage. Not the integration target for the mature V2 work. |
| `feat/company-watch-isolated-20261117` | Source branch for merged PR #72. | Historical source of the isolated watcher. |
| `fix/company-watch-ats-adapters-20261117` | PR #73 remains open, draft and unmerged; head `6a41c8125464c672d3b73e8196faeec077b9c05b`. | Contains Workday/Workable/SmartRecruiters detail fixes and the report artifact upload fix. Keep as a dry-run prototype. |
| `v2-live-radar` | Mature integration/release branch inspected at `5c28d97ea39edfa8af13d9686f7b97c3997901f3`. PRs #65, #66 and #67 have been merged here. | **Target for V2 integration.** |
| `docs/company-watch-v2-integration-handover-20261117` | Documentation-only planning branch created for this handover. | Review and merge only the docs plan when accepted. |

PR #73 is based on `main`, not `v2-live-radar`. Do not merge or cherry-pick the whole Company Watch branch into V2 as a shortcut. It duplicates collectors already present in V2, uses a second filter engine and includes its own send path. Reuse only its curated data and any narrowly useful research after comparing it with the V2 adapter contract.

References:
- [PR #72 — isolated Company Watch](https://github.com/AvinashBhalla/job-beeper/pull/72)
- [PR #73 — Company Watch ATS and report fixes](https://github.com/AvinashBhalla/job-beeper/pull/73)
- [PR #65 — global ATS candidate staging](https://github.com/AvinashBhalla/job-beeper/pull/65)
- [PR #66 — per-board scheduler](https://github.com/AvinashBhalla/job-beeper/pull/66)
- [PR #67 — bounded global ATS discovery](https://github.com/AvinashBhalla/job-beeper/pull/67)

## 3. What is already implemented in V2

This is not a greenfield rewrite. The following foundations exist on `v2-live-radar`.

### 3.1 Provider collectors

`v2/radar.py` registers 12 collectors:

- Marketplaces/global feeds: LinkedIn, Naukri relay, Instahyre.
- Employer ATS collectors: Greenhouse, Ashby, Lever, Workday, SmartRecruiters, Workable, Keka and Darwinbox.

Examples of existing source-specific detail coverage:

- Greenhouse requests the public Job Board API with `content=true`.
- Ashby and Lever consume their public posting fields.
- Workday uses its public Candidate Experience/CXS board API, with bounded details, inventory paging/facets and per-board state.
- SmartRecruiters has bounded pages and posting-detail requests.
- Workable consumes its public published-jobs widget.
- Keka and Darwinbox have provider-specific public career feed adapters.

These adapters already return the common normalized job shape and participate in the V2 ingestion path. Do not add second copies from Company Watch unless a proven capability gap remains after tests.

### 3.2 Company and ATS board discovery

`v2/board_discovery.py` has a review-first public careers-site scanner. Its provider pattern list recognizes Workday, Greenhouse, Ashby, Lever, SmartRecruiters, Workable, Keka, Darwinbox and several discovery-only ATS families. The distinction is deliberate:

- Detection means a URL looks like a provider board.
- `collector_available` means a V2 collector exists.
- Discovery does not mean the board is verified.
- Verification does not mean the board is active.
- Activation is a separate administrator action.

The module already exposes public employer/careers-page discovery. It limits page count, validates public HTTPS destinations and redirect targets, and returns board candidates for review. Discovery-only providers must not be advertised as active V2 ingestion sources.

### 3.3 Registry, verification and activation

`v2/radar.py` creates two additive tables:

- `ats_board_registry`: company-linked provider/board identity, URL, provenance, confidence, collector availability, review state, verification timestamps, errors and baseline state. Unique key: `(company_id, provider, board_key)`.
- `ats_global_discovery_candidates`: unmatched public ATS candidate URLs with host-aware identity, discovery method/reference, capture time, first/last seen, confidence, review status and optional links to a real company/board. Unique key: `(provider, candidate_host, board_key)`.

Existing admin APIs implement the lifecycle:

1. `POST /api/discovery/companies/scan` discovers provider board candidates from a submitted real employer website/careers URL and saves them as `discovered`.
2. `POST /api/discovery/global-candidates/import` stages unmatched Workday/Keka/Darwinbox URLs. It does not create employer or active board records.
3. `POST /api/discovery/global-candidates/{id}/link` links a staged candidate to an existing employer record. Linking is not verification or activation.
4. `POST /api/discovery/boards/{id}/verify` probes the provider's public endpoint and marks the board `verified`. A board without an implemented collector cannot be verified for polling.
5. `POST /api/discovery/boards/{id}/activate` accepts only a verified board. It writes the provider-specific entry to the current runtime config, links `registry_id`, enables the global source flag, marks the board active/baseline-pending and syncs the persistent scheduler.
6. `POST /api/discovery/boards/{id}/deactivate` removes only that board's linked provider config entry and turns off the provider flag only when no peer boards remain.

**Integration implication:** Company Watch should feed stages 1–3, not bypass stages 4–6.

### 3.4 Per-board scheduler

`v2/board_scheduler.py` already provides persistent scheduling:

- `ats_board_poll_schedule` and `ats_board_host_poll_state` tables.
- Per-board due time, provider config and registry ID.
- Atomic leases and at most one active board poll per API host.
- Global concurrent-host cap of 3.
- Host minimum interval, persisted 429 cooldowns, per-board failure backoff, last outcome and metrics.
- A newly added/reactivated board begins with `baseline_pending=1`.
- Normal config sync preserves due times and poll history.

The important remaining architecture issue is that `configured_boards(config)` and `sync_config(...)` currently derive the scheduler set from global `source_enabled` and provider `*_boards` arrays in runtime config. The DB registry is not yet the sole source of truth. For this initial Company Watch integration, use the existing verified activation path; do not replace scheduler reconciliation in the same increment.

### 3.5 Shared job storage, deduplication and user matching

The existing V2 path is:

```text
verified active ATS board
  -> existing provider collector
  -> normalized job observation
  -> upsert_jobs() into SQLite
  -> canonical opportunity linking/deduplication
  -> persisted evaluation against each active user's preferences
  -> user_notification_ledger
  -> per-user opt-in Telegram dispatch
```

- Stable `(source, source_job_id)` uniqueness is enforced in `jobs`.
- `v2/dedupe.py` provides conservative cross-source canonical linking.
- `upsert_jobs()` calls `refresh_configured_user_evaluations(affected_job_ids)` after commit.
- `v2/user_preferences.py` owns profile preferences and `user_job_evaluations`.
- `v2/user_notifications.py` owns member opt-in settings, the per-user ledger, chat-target validation, pre-send revalidation and dispatch.
- The background notification worker calls `user_notifications.dispatch` independently of the legacy/admin Telegram sender.
- `MATCHER_RULES_VERSION` currently equals 3. Matcher-rule changes require a deliberate version bump and fingerprint regression tests.

**Important clarification:** per-user preferences currently describe role, skills, location, experience, title exclusions, match threshold and age. They do not currently have per-user provider toggles. That is not a blocker for this work: ingest shared jobs once, then match each job against each user's saved role/profile preferences. Do not put company-board identifiers into user preferences.

## 4. Company Watch inventory — how to interpret it

The Company Watch branch `fix/company-watch-ats-adapters-20261117` contains a 100-row `company_watch/companies.csv`.

The inspected PR #73 head has:
- 100 registry rows.
- 92 `scan_enabled=True` rows and 8 held for manual review.
- Current scan-mode distribution: 72 generic `careers_page`, 9 Greenhouse, 5 Lever, 3 SmartRecruiters, 1 Ashby, 1 Workday, 1 Workable and 8 manual-review rows.

The `scan_enabled` flag means “candidate was included in the isolated Company Watch canary.” It does **not** mean:
- the V2 company identity is confirmed;
- a V2 registry row exists;
- the provider endpoint has been verified under V2's verifier;
- the board is active or safe to poll;
- the job descriptions are complete;
- the source is permitted/unblocked for every request path.

In particular, 72 rows are generic careers pages, not 72 identified ATS boards. They must first pass the V2 careers/ATS discovery path. If discovery only returns generic links or no structured `JobPosting`, hold them for review until a dedicated V2 generic-careers ingestion adapter has a scoped security/policy and quality design.

### Provider mapping

| Company Watch mode | V2 destination | Import/review rule |
|---|---|---|
| `greenhouse` | `greenhouse` collector | Parse canonical board slug from a validated public Greenhouse URL; link only to a verified employer record. |
| `lever` | `lever` collector | Parse site slug and EU/global host variant; don't lose provider instance in board identity. |
| `ashby` | `ashby` collector | Parse board identifier from the official public board URL; preserve stable source job ID. |
| `smartrecruiters` | `smartrecruiters` collector | Parse company identifier; verify public `destination=PUBLIC` endpoint. |
| `workday` | `workday` collector | Preserve tenant + cluster host + site identity; don't treat a search page path as a generic slug. |
| `workable` | `workable` collector | Parse verified account slug; verify public published-jobs endpoint. |
| `careers_page` | No generic page collector in the V2 `COLLECTORS` registry | Run employer/careers discovery. Use a detected supported ATS board if found; otherwise stage as a generic page lead for a later adapter/review. |
| `manual_review` | No collector | Retain as unresolved; do not poll. |

The Company Watch modes are compatible with several V2 collector types, but the Company Watch adapters themselves should not be copied into V2 without proving a gap. V2 has additional scheduler, metrics, rate-limit and baseline behaviour that Company Watch does not own.

### Evidence from the latest isolated scan

Company Watch workflow run [#3 / 44043855196](https://github.com/AvinashBhalla/job-beeper/actions/runs/44043855196) completed successfully and uploaded `company-watch-report-3` with JSON and Markdown. The reported summary was:

| Metric | Result |
|---|---:|
| Companies scanned | 78 |
| Manual review | 8 |
| Board failures | 14 |
| Jobs observed | 1,338 |
| New matches (Company Watch's own rules) | 0 |
| New review candidates | 3 |
| Rejected | 1,318 |
| Already seen | 17 |

The 14 failures were 9 blocked (401/403), 3 rate-limited (429), 1 timeout and 1 TLS failure. Three roles were placed in review because the scan did not have usable JDs (two Walt Disney roles and an Under Armour role). This is evidence for an acquisition/JD-quality problem; it is **not** evidence that the V2 preferences would produce zero matches. The two matchers are different.

## 5. Why the independent Company Watch matcher and send path must not be integrated

Company Watch currently has:
- `company_watch/filters.json` with a separate title include/exclude, India-location regex, skills regex and a fixed two-year experience rule.
- `judge()` in `company_watch/scan.py`, which makes independent `match/review/reject` decisions.
- URL-based `.state/seen.json` state, independent of V2 canonical IDs and source/job DB rows.
- Its own optional `send_telegram()` / `--send` path.

This creates predictable divergence:
- Company Watch's seniority regex includes `sr\.` but not the bare `sr` token; the V2 preference list has its own explicit `sr` exclusions and normalization.
- Company Watch's max-years rule is fixed at 2, while the V2 user preferences store candidate experience and configured min/max job-experience constraints.
- Company Watch's location rule is India-only and regex-based; V2 has India-aware remote and explicit location normalization rules.
- Company Watch can mark a URL “seen” even when it was only a review candidate. If the detail is available later, URL-state dedupe can hide the improved record.
- The Company Watch report provides high-level rejected counts but no adequate per-reason rejection distribution for matcher-quality analysis.
- A second Telegram sender would bypass V2 dedupe, baseline, user opt-in, per-user chat and pre-send revalidation.

**Decision:** `filters.json`, `judge()`, URL-only `seen.json` and `send_telegram()` are prototype-only. Do not migrate them into the production V2 path.

## 6. Highest-priority correctness gaps to solve

### P0 — Reconcile registry candidates without creating false employers/boards

Current global candidate import normalization accepts only Workday, Keka and Darwinbox. Company Watch includes Greenhouse, Lever, Ashby, SmartRecruiters and Workable too. The importer needs a provider-specific extension before the whole CSV can be staged. This must use strict fixed-host/path/identifier validation and the existing collector availability map. It must not accept arbitrary HTTPS pages as ATS candidates.

Recommended import shape:
- Parse and validate the CSV into immutable source records with row number and source file hash.
- Resolve provider URL using `board_discovery.detect_ats_board()` or a provider-specific canonicalizer.
- Resolve the employer using the existing `employer_companies` canonical website/domain record or a separately verified employer website.
- If one exact employer mapping is not available, stage the board candidate without inventing a company or using the ATS provider host as a fake corporate domain.
- Use `ats_global_discovery_candidates` for genuinely unmatched supported provider board URLs. Extend its importer to the additional public provider patterns with regression tests.
- If the company can be safely matched or created from a verified official domain, insert/update `ats_board_registry` with `review_status='discovered'`, not `verified` or `active`.
- Preserve the CSV row number, original career URL, verification source/note, import batch ID, import timestamp, source file hash and any alias/identity decision as provenance.
- Import is idempotent: same company + provider + board key updates provenance/last_seen, never duplicates board or company rows.
- Disabled/manual rows remain excluded from automated verify/activate, but their identity evidence may be displayed for admin review.

Do not treat “company name matches after lowercasing” as sufficient. Use a verified canonical domain and explicit conflict handling for subsidiaries, brands, aliases, multiple ATS boards or duplicate names. A single company may have more than one board or provider.

### P0 — Make JD completeness explicit and durable

Company Watch's generic link fallback returns titles and URLs without a JD. Some V2 source APIs return description snippets or partial detail. Today the `jobs` schema persists descriptions and experience provenance, but there is no first-class JD fetch/completeness state.

Add an additive, migration-safe JD state. Proposed fields (final names to be chosen in implementation):
- `jd_status`: `complete | partial | unavailable | fetch_failed | not_required`.
- `jd_fetched_at`.
- `jd_content_hash`.
- `jd_source_updated_at` (only when the source exposes a trustworthy update timestamp).
- `jd_provenance` / `jd_completeness_reason` (provider detail field, JSON-LD, safe HTML fallback, summary-only, blocked, timeout, etc.).

Rules:
- “Complete” should mean the provider's real job-detail/full-description field was retrieved and parsed, not merely that an arbitrary string is non-empty. The exact source-specific contract must be documented and tested.
- A search-card summary is `partial`; no description is `unavailable`; access/timeouts are `fetch_failed`.
- Fetch provider detail endpoints first. A generic URL fallback must validate HTTPS, resolved IPs/redirect destinations, content type, response byte cap, timeout and allowed host/path. Never follow arbitrary external redirects without re-validation.
- Fetch only new, partial, or materially changed JDs. Cache by canonical source job identity plus content hash; don't redownload unchanged descriptions every poll.
- Keep source provenance and extraction provenance separate. A parser-derived experience range is not equivalent to an employer-stated structured requirement.
- Initially gate Company Watch-origin/newly integrated source notifications on `jd_status='complete'`. Keep partial/unavailable/fetch_failed jobs visible in a review state. Do not impose this new rule on existing provider alerts until an evidence-based separate decision is made.
- The JD gate must be checked both while queuing per-user notifications and immediately before sending. Otherwise a stale queued notification could bypass a new completeness policy.

### P0 — Correct the job update semantics for changed JDs

In `upsert_jobs()`, a plain-text description currently replaces the stored description only when it is longer than the previous plain-text value. This protects a full JD from a short search snippet, but it also means a real updated JD of equal or shorter length can be ignored.

Modify only after adding deterministic regression cases:
- Keep a richer known-complete description when an incoming observation is clearly only a summary/partial.
- Replace the saved JD when the source indicates a material update and a newly fetched complete JD has a different content hash, even if its length is the same or shorter.
- When the JD hash, source update metadata or relevant extracted experience changes, invalidate/recompute the persisted job evaluation and every affected user's evaluation.
- When no trustworthy source update timestamp exists, compare content hashes and preserve first-seen/publication metadata separately.
- Never make a new source observation look like a new job or reset `first_seen_at`.

### P1 — Measure filter quality and expose reasons

The V2 matcher is already the one decision-maker. Do not tune score weights before a representative sample is labelled.

Extend the existing matcher quality benchmark with manually reviewed Company Watch examples:
- clear positive: target title, target location, relevant responsibilities/skills, compatible experience;
- hard negatives: seniority/title exclusion, unrelated category despite incidental technical keyword, location mismatch hidden in multi-location description, experience above profile;
- review-only: JD missing, incomplete or contradictory source data;
- positive with generic title but relevant JD, so the integration does not lose roles before fetching the details.

Report match score, hit/reject reasons, JD status, source/provider and manual label. Measure precision on the labelled set; never call the 5-example starter benchmark a statistically representative precision estimate.

Add structured rejection counts to shadow reports. Suggested categories:
- excluded title/role;
- no target role;
- location mismatch;
- experience mismatch;
- skills/role signal absent;
- JD incomplete/unavailable;
- stale posting;
- duplicate canonical opportunity;
- source/verification failure.

Do not use AI/LLM matching in this initial quality gate. The deterministic matcher is explainable and already shared with the app. Gemini's existing shadow extraction path must remain shadow-only and must not silently influence alerts.

### P1 — Keep per-board lifecycle and scheduler state consistent

Use the current safe lifecycle first:
`discovered -> linked -> verified -> active -> deactivated/verified`.
- Verify every new board before activation.
- Do not activate discovery-only providers or generic page URLs.
- Do not use Company Watch's 92-row `scan_enabled` state to set global V2 source flags.
- Activation must stay idempotent. Re-import or repeated activation must not reset another board's due time, host cooldown, lease or baseline.
- Deactivation removes only the registry-linked provider entry; it must not disable peer boards that share the provider.
- Preserve `baseline_pending` so the first full inventory is silent; do not backfill a historic vacancy archive into Telegram.
- Test partial-board failures and 403/429 behaviour. A blocked board is not “dead” and must not be retried via access-control bypass.

Later, consider making `ats_board_registry` the single source of truth for scheduler eligibility. This is a separate migration: provide an idempotent reconciliation path from existing `*_boards` config arrays, preserve active rows/leases/due times/cooldowns, and prove rollback before removing config-array support. Do not combine it with the first Company Watch import.

## 7. Recommended target flow

```text
Company Watch CSV + official source evidence
  -> strict manifest parser / provenance
  -> resolve real employer identity (or keep unmatched candidate)
  -> ATS URL canonicalization and provider allowlist
  -> ats_global_discovery_candidates / ats_board_registry [discovered]
  -> human review for identity conflicts and ambiguous boards
  -> V2 public endpoint verification [verified]
  -> explicit admin activation [active + baseline_pending]
  -> existing board_scheduler + existing V2 provider collector
  -> JD status/enrichment and material-change detection
  -> existing upsert_jobs + canonical_opportunity dedupe
  -> existing user_job_evaluations using each user's saved preferences
  -> existing user_notification_ledger with opt-in + pre-send revalidation
  -> existing per-user Telegram dispatch
```

There is no independent Company Watch production polling loop, second matcher, URL `seen.json` or Company Watch Telegram sender in this target flow.

## 8. Delivery sequence — one safe phase at a time

### Phase 0 — Baseline and no-regression contract

- Start from a fresh isolated checkout of exact `v2-live-radar` head. Do not use the dirty VM checkout until the owner/operations admin resolves its branch lag and Docker access safely.
- Run baseline Python compilation and the full V2 test suite in a clean environment; record exact commit, command, exit code and test count.
- Capture a read-only dev/QA baseline: container image/commit, DB integrity, jobs/source_runs counts, board registry by provider/state, scheduler active boards/leases/cooldowns, source flags, notification flags/credentials-presence (never values), queued/sent ledger counts.
- Preserve existing local `v2/config.json`, `.env.save`, `.venv/` and `v2/config.json.backup.20261105-183321`. Do not run `git reset`, `git clean`, checkout replacement, config overwrite or compose restart on that checkout.

Acceptance: baseline is captured and no runtime or notifications changed.

### Phase 1 — CSV manifest and registry import, no polling

- Write a parser/validator for the 100-row CSV. Preserve all columns, row number and source hash.
- Map provider URL modes to the existing V2 provider identities.
- Resolve companies by verified employer domain. If identity is ambiguous, stage as unmatched candidate or hold for admin mapping.
- Extend the current candidate import only for supported provider patterns needed by the CSV (Greenhouse, Ashby, Lever, SmartRecruiters, Workable, Workday). Do not automatically import generic pages as ATS boards.
- Import the 92 enabled rows as review candidates; keep 8 manual rows visibly held. Do not activate any row from the CSV's `scan_enabled` flag.
- Produce an import report: exact match, candidate linked, duplicate, conflict/ambiguous, unsupported/generic, invalid URL and manually disabled counts.

Acceptance: re-running the same import is idempotent; zero boards are active/scheduled solely because of import; zero source requests and zero Telegram messages.

### Phase 2 — Verification and limited board activation in isolated QA

- Use the existing verify endpoint. Classify blocked 401/403, 404, 429, timeout, TLS and parser errors distinctly.
- Verify at most a small, owner-reviewed sample across already implemented providers; don't test all 92 in one burst.
- Activate only the explicit allowlisted sample through the current activation endpoint.
- Confirm each board has one registry row, one schedule row, one host lease domain, baseline pending before its first poll, and no duplicated provider config entries.
- First poll must baseline historical inventory silently; second poll must prove new unique jobs can be ingested.

Acceptance: stable repeated schedule state, no duplicates, no historic alert burst, no production effect.

### Phase 3 — JD completeness and shadow evaluations

- Add the schema fields with additive migrations.
- Implement a bounded source detail fetch/enrichment path with provider-specific rules and a cache.
- Run integrated jobs through V2 matching using existing preferences, but do not send notifications for this source cohort.
- Save match score/reasons, JD status, parse provenance, canonical ID and “would alert” decision.
- For incomplete JD, keep the record for review and ensure it cannot queue/dispatch an automatic Company Watch-origin alert.
- Re-import/re-poll an updated JD to prove content hash/change detection and user evaluation invalidation work.

Acceptance: no second matcher; every reviewed match decision can be explained; incomplete JDs remain visible but non-alertable; existing source behaviour unchanged.

### Phase 4 — Quality audit and pilot selection

- Manually label a representative positive/negative/review set from actual V2-captured JDs.
- Review false positives and false negatives, not only top scores.
- Inspect reasons per rejection; tune preference semantics only with owner-approved examples and deterministic tests.
- Select a small pilot set of verified boards with good JD completion and stable API health.

Acceptance: agreed precision threshold on a defined manually labelled set, JD completeness threshold, known 403/429 rate and operational budget.

### Phase 5 — Limited alert pilot

Only after owner review:
- Enable per-user notifications for selected pilot cohort through existing opt-in/settings.
- Test one genuinely new posting in an isolated QA account first.
- Verify queue -> claim -> pre-send revalidation -> sent ledger; test opt-out and preference change cancelling the send.
- Expand the selected board allowlist gradually. Do not change the shared provider poll cadence without separate measurement.

Production rollout remains a separate explicit approval gate.

## 9. Required tests

At minimum add unit/integration coverage for:

**Manifest/identity**
- CSV schema/100 rows, 92/8 state, row count stability, import idempotency.
- Every supported mode canonicalizes to the right V2 provider/key/host.
- URL rejection for non-HTTPS, user-info, nonstandard ports, localhost/private IP, unexpected hosts/paths, redirects to disallowed destinations.
- Duplicate company/domain, aliases, multiple boards and cross-company board conflict.
- Generic careers page and disabled/manual row cannot activate as a guessed ATS.

**Registry/scheduler**
- Import creates only `discovered` candidates.
- Link is not verify; verify is not activate.
- Unsupported collector cannot verify/activate.
- Verified-only activation; deactivation removes one board and preserves provider peers.
- Repeat activation/import is idempotent; unrelated board due time, lease, host cooldown and baseline remain unchanged.
- First poll baseline and second poll fresh-new-job behaviour.
- 403 and 429 never trigger bypass.

**JD/normalization**
- Provider full description vs partial summary mapping.
- Workday/SmartRecruiters detail failures remain visible and retryable rather than promoted.
- Empty/partial/full/fetch_failed states.
- Same/shorter-length changed JD replaces old JD only when source evidence says it is a material complete update.
- Shorter summary does not overwrite a known complete JD.
- Content hash stable on unchanged content; hash change re-evaluates both shared and per-user evaluations.
- Source ID and canonical URL stable across polls; cross-provider duplicates link conservatively.

**Matching/notifications**
- Existing `match_details()` outputs stay identical for existing source fixtures.
- Existing user preferences remain authoritative; Company Watch filters never override them.
- A Company Watch-origin job without complete JD cannot queue or dispatch.
- Both queue and final-send revalidation enforce the JD gate.
- Per-user enabled/disabled settings, enabled_at no-backlog boundary, private chat destination, preference fingerprint and opt-out remain enforced.
- No direct call to Company Watch `send_telegram()`.
- Matcher logic change increments `MATCHER_RULES_VERSION`; operational/board settings do not invalidate every evaluation.

## 10. Runtime/deployment snapshot — 2026-11-17, read-only

Termalin host `job-radar` responded to a read-only SSH check. No files or services were changed.

| Item | Observed result |
|---|---|
| Development checkout | `/home/ubuntu/job-beeper-dev`, branch `v2-live-radar`, HEAD `7ebc38b7c321847e74895557551478c3ff11bd4a`, **147 commits behind** `origin/v2-live-radar` |
| Development checkout local state | Modified `v2/config.json`; untracked `.env.save`, `.venv/`, `v2/config.json.backup.20261105-183321` |
| Production checkout | `/home/ubuntu/job-beeper`, branch `v2-live-radar`, HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34`, **613 commits behind** `origin/v2-live-radar`; no local changes shown by `git status` |
| Docker access | `docker ps` returns permission denied on `/var/run/docker.sock`; socket is `root:docker` mode `0660`; the current `ubuntu` user is not in the `docker` group |
| Port 8000 health | TCP connection succeeds but HTTP health request times out (HTTP 000) |
| Port 8001 health | Connection reset by peer (HTTP 000) |
| Port 8010 health | HTTP 200 |
| Port 8006 health | HTTP 200 |
| Port 18011 health | HTTP 200 |

A listener was present on all five loopback ports. The roles of ports 8010/8006/18011 align with older QA/candidate docs, but current container identity/image/volume was not verifiable because Docker access was denied. Do not infer exact deployment image, database, source flags or Telegram state from these checks.

**Operational hard gate:** do not pull, reset, clean, overwrite config, restart Compose, rebuild images, alter Docker socket permissions, add the user to the Docker group or touch production. Preserve the dirty dev files exactly. Before any runtime rollout, an authorized operations path must reconcile the 147/613-commit lag and provide read-only Docker/health/DB evidence. Never use `sudo` or bypass host access controls as a workaround.

## 11. Work completed in this planning task

- Read V2 source code and architecture at `5c28d97ea39edfa8af13d9686f7b97c3997901f3`.
- Confirmed Company Watch's 100-row/92-enabled/8-manual inventory and provider mode distribution on PR #73 head.
- Confirmed V2 collectors already exist for Greenhouse, Lever, Ashby, SmartRecruiters, Workday and Workable; generic career-page ingestion is not a current V2 collector.
- Confirmed V2 candidate import currently accepts only Workday/Keka/Darwinbox; Company Watch importer needs provider-aware extension.
- Confirmed V2 verification and activation are distinct and activation uses provider config arrays plus persistent per-board scheduler.
- Confirmed shared SQLite upsert, canonical dedupe, per-user preference evaluation and per-user notification dispatch exist.
- Identified the current shorter/equal-length JD update limitation in `upsert_jobs()`.
- Identified the absence of a first-class JD completeness field and automatic alert gate for the new source cohort.
- Rechecked Termalin in read-only mode and documented the local branch lag, dirty files, Docker permission error and HTTP health results.
- Created this plan and updated the agent handover pointers in the same documentation-only branch.

**No code, configs, databases, credentials, source schedules, notifications, deployments, containers or running services were changed.** No tests were run locally. The exact-head GitHub CI result is recorded below.

## 12. Exact-head GitHub CI result — 2026-11-17

- Documentation PR: [#74](https://github.com/AvinashBhalla/job-beeper/pull/74), current head `2be95c5b5adb3a48dd8c48aa8d0e74da0e1c1f64`; latest tested merge commit `a6ab3bdfe77dd041fb74bfed58fd6d75459c84ab` against base `5c28d97ea39edfa8af13d9686f7b97c3997901f3`.
- Latest [V2 CI run #1484](https://github.com/AvinashBhalla/job-beeper/actions/runs/44056563963) completed with **failure**. Previous run #1482 on the prior docs head failed with the same test failures.
- Successful steps: Python compilation, dashboard JavaScript syntax, focused router/extractor tests (32/32).
- Full V2 suite: **484 tests in 59.473 seconds; 10 failures and 2 errors**. All 12 are in `v2/test_user_notifications.py`.
- Errors: `test_permanent_telegram_client_error_is_not_retried` and `test_transient_delivery_failure_is_recorded_for_retry` read a missing ledger row (`NoneType`).
- Failures: `test_baseline_marker_blocks_a_previously_queued_item_before_send`, `test_canonical_baseline_marker_blocks_final_send_revalidation`, `test_canonical_baseline_marker_cancels_previously_queued_member_item`, `test_current_nonmatching_evaluation_cancels_previously_queued_notification`, `test_dispatch_sends_only_to_owner_chat_and_marks_sent`, `test_initial_source_baseline_jobs_are_not_queued_for_any_member`, `test_preference_change_cancels_a_queued_job_that_no_longer_has_a_fresh_evaluation`, `test_queue_is_idempotent_for_same_user_and_opportunity`, `test_queue_is_user_scoped_and_never_replays_pre_opt_in_jobs` and `test_two_users_receive_only_their_own_matching_job_and_chat`.
- The PR diff is documentation-only and changes no application or test code. No base-SHA workflow run was available through the connected GitHub history, so do not label the failures as proven pre-existing or caused by this docs PR.
- **Gate:** keep PR #74 draft/unmerged. Before Company Watch code integration, reproduce and diagnose the notification-suite failures on a clean checkout of the exact base SHA, then rerun the full suite. Do not weaken assertions or alter notification behaviour merely to make CI green. No runtime, source, database, scheduler, deployment or Telegram state was changed by this documentation task.

## 13. Next agent — exact ordered checklist

1. Read this document first, then the newest entry at the top of `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`.
2. Work from a fresh clean checkout of exact `v2-live-radar` remote HEAD in a separate safe workspace. Do not reuse or pull the dirty VM working tree.
3. Capture baseline tests and source/board/notification state in an isolated DB/QA environment. No production.
4. Implement Phase 1 manifest parser/import in a feature branch, with no polling and no activation; send the proposed import report for review.
5. Implement Phase 2 verification/activation only after import tests pass. Limit to a small manually reviewed subset.
6. Implement additive JD status/hash fields and update handling with focused migrations/tests. Keep incomplete Company Watch-origin jobs non-alertable through both queue and pre-send checks.
7. Add labelled matcher examples and rejection reason reporting; compare against the existing V2 preferences, not Company Watch's `filters.json`.
8. Run full V2 tests and exact-head GitHub CI. Deploy only to isolated QA after host access/checkout evidence is resolved.
9. Observe a measured shadow canary (at least repeated scheduled runs) and record unique matches, JD completeness, precision labels, p50/p95 latency, HTTP 403/429/5xx, request count, duplicate rate and DB integrity.
10. Obtain explicit owner approval before any production rollout or notification activation.

### User input

Nothing is required from the owner to finish this documentation/planning increment. Later, the only likely owner decisions are:
- resolve real-employer identity for any genuinely ambiguous Company Watch rows;
- approve the manually reviewed pilot boards/quality threshold;
- explicitly approve per-user Telegram pilot and production promotion.

Do not ask the owner to resend the 100-company list or explain the filter intent; it is in the repository and this handover.

### Continuation prompt

> Continue the Company Watch → V2 integration from `docs/COMPANY_WATCH_V2_INTEGRATION_HANDOVER_2026-11-17.md`. Target `v2-live-radar`, not `main` or PR #73. Keep Company Watch as a curated discovery manifest only. Phase 1 must be a strict, idempotent registry import with no polling or activation. Reuse V2 provider collectors, verification, per-board scheduler, shared upsert/canonical dedupe, saved user preferences and per-user notification dispatcher. Add first-class JD completeness/hash and updated-JD handling; gate only the new source cohort until validated. Do not merge PR #73 into V2, copy its separate matcher/sender, enable notifications, or touch production. The dev VM checkout is dirty and 147 commits behind; production is 613 behind; Docker is not available to the current user. Preserve all local files and request authorized ops access rather than resetting or using sudo. Update both handover docs after every prompt.
