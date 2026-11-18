# Company Watch correction and review checkpoint — 18 November 2026

## Purpose

Bring the V2-pinned Company Watch snapshot into line with the latest reviewed source CSV on main, without creating employer records, linking boards, verifying boards, changing source flags, activating boards, adding schedules, or sending notifications.

## Source and integrity

- Source: company_watch/companies.csv
- Source ref: main@da7e42dbaaeee0a89ebdde92799aee8db7543ec6
- Pinned snapshot: v2/data/company_watch_companies_2026-11-18.csv
- SHA-256: 146582ae4f3d68a9f13eff23b90bcf2ef5f28c9ab2020948d1ffaf82a5e7e4bd
- Rows: 100; enabled: 92; disabled: 8
- Expected V2 classification: 19 candidate_staged; 81 manual_review

## Reviewed row changes

| Row | Company | Previous classification | Current classification | Decision |
|---|---|---|---|---|
| 2 | Mistral AI | Lever mistral | Ashby mistral.ai | Stage corrected Ashby candidate; official Mistral careers page is provenance |
| 13 | SoundHound AI | Greenhouse soundhoundinc | Generic official careers page | Manual review; do not guess another ATS slug |
| 36 | The Standard | Manual / Workday adapter gap | Workday candidate | Stage review-only; V2 supports the Workday candidate normalizer |
| 43 | Caxton Associates | Workable candidate source | Manual review | Keep manual: V2 explicitly treats the verified_workable_board status as ambiguous, even though Workable URL normalization exists. Do not remove this safety gate as part of this correction |

The manifest's verified_* labels are source evidence, not V2 live verification. All imported candidates remain low-confidence and unlinked. The current manifest contains 19 candidate rows and 81 manual-review rows; the existing production candidate table will temporarily retain the two superseded candidates until they are explicitly rejected.

## Safe import and stale-candidate handling

The V2 importer is pinned by both source ref and SHA-256. The import is atomic and idempotent. It only writes manifest audit rows and unmatched global ATS candidates.

After this branch is reviewed, merged, and deployed under the normal release gates:

1. Run the Company Watch dry-run first. It must report 100 rows, 19 candidates, 81 manual-review rows, and the exact SHA-256 above.
2. Import using the admin-only Company Watch import endpoint.
3. Confirm the ten production registry boards and ten schedules are unchanged; confirm zero new employer records, zero linked/verified/active boards, zero new schedules, zero network requests and zero notifications from the import.
4. Find the old candidate by provider/key lever/mistral and reject it through the admin-only global-candidate review endpoint. Current production candidate ID: 1.
5. Find the old candidate by provider/key greenhouse/soundhoundinc and reject it through the same endpoint. Current production candidate ID: 6.
6. Confirm the new ashby/mistral.ai and workday/standard candidates exist as discovered; SoundHound and Caxton must have no ATS candidate from these manifest rows.
7. Do not link, verify, activate, or schedule any of these candidates as part of this correction.

Use provider/key rather than hard-coded IDs when performing the review; IDs can change if other candidates are imported first. The two IDs above are only the current production observations.

## Explicit non-goals

No production database write is part of this PR. No direct SQL patching, board activation, source allowlist changes, polling changes, search API integration, recurring discovery worker, Telegram, or member-feature work is included. The production 24-hour source reliability window remains a separate acceptance gate.

## Offline dry-run qualification — 18 November 2026

The current merged `v2-live-radar` checkout was cloned into a disposable directory and the pinned manifest dry-run was executed inside the existing production application image with Docker networking disabled. This calls the same `radar.import_company_watch_manifest({dry_run: True})` path as the admin route but returns before any DB write.

- Manifest SHA-256: `146582ae4f3d68a9f13eff23b90bcf2ef5f28c9ab2020948d1ffaf82a5e7e4bd` (exact pinned hash).
- Rows: **100**; candidate_staged: **19**; manual_review: **81**.
- Reported side effects: companies created 0; boards linked 0; verified 0; activated 0; scheduled 0; network requests 0; notifications 0.
- The dry-run assertion suite passed. No dry-run SQLite file was created, confirming this path did not open or mutate a DB.
- This is offline manifest/parser qualification, not a deployment, import, endpoint verification or production change. At the time of this pre-release offline checkpoint, the corrected manifest had not yet been imported; the subsequent production execution is recorded in the final section below.


## Production import and guarded correction — 19 November 2026

The earlier offline-only section above records the state before promotion. The correction has since been deployed and imported into production under the approved final release gate.

- Candidate runtime path: /app/v2/data/company_watch_companies_2026-11-18.csv
- Source ref: main@da7e42dbaaeee0a89ebdde92799aee8db7543ec6
- SHA-256: 146582ae4f3d68a9f13eff23b90bcf2ef5f28c9ab2020948d1ffaf82a5e7e4bd
- Production runtime dry-run with payload {"dry_run": true}: 100 rows, 19 candidate_staged, 81 manual_review, 0 invalid; companies created 0, boards linked 0, verified 0, activated 0, scheduled 0, network requests 0, notifications 0.
- Production import via radar.import_company_watch_manifest({}) completed at 2026-11-18 21:17:20.785205 UTC / 2026-11-19 02:47:20.785 IST.
- Import result: 2 candidates inserted, 17 updated, 0 terminal candidates preserved. The result was recalculated first against a fresh online-backup copy of the current production DB using the exact candidate image; all pre-existing candidate IDs, statuses and linkage fields were verified unchanged by import.
- New review-only candidates: ashby/mistral.ai (jobs.ashbyhq.com) and workday/standard:search (standard.wd1.myworkdayjobs.com). Both remain discovered and unlinked.
- The two obsolete candidates were resolved by provider + board_key at execution time and rejected only through radar.review_global_ats_candidate: lever/mistral and greenhouse/soundhoundinc. Both function results returned activated=false.
- Final candidate table: 21 rows total; 19 discovered and 2 rejected. No unrelated candidate status or linkage changed.
- Manifest audit: 100 rows / 19 staged / 81 manual / 0 invalid; all 100 manifest audit rows persisted under the exact pinned hash.
- Employers remain 10; active registry boards remain 10; active schedules remain 10; exact keys unchanged. No employer, board, link, verification, activation or schedule was created.
- Notification ledger stayed at 27,725; importer reported zero network requests and zero notifications. SQLite quick_check: ok.

Production is running job-radar-prod-release:dda6d57 (image ID sha256:bbf5252047ed2b3bbc8d06f7c51663e6deae4be28d9c82fdfc65e9a8b005ba5d). Health, dashboard and OpenAPI are HTTP 200; no restart/OOM. The rollback image remains available. Naukri relay remains disabled; SERP remains inactive with no credentials or paid requests. Issue #99 remains P2 next release.
