# Company Watch correction and review checkpoint — 18 November 2026

## Purpose

Bring the V2-pinned Company Watch snapshot into line with the latest reviewed source CSV on main, without creating employer records, linking boards, verifying boards, changing source flags, activating boards, adding schedules, or sending notifications.

## Source and integrity

- Source: company_watch/companies.csv
- Source ref: main@da7e42dbaaeee0a89ebdde92799aee8db7543ec6
- Pinned snapshot: v2/data/company_watch_companies_2026-11-18.csv
- SHA-256: 146582ae4f3d68a9f13eff23b90bcf2ef5f28c9ab2020948d1ffaf82a5e7e4bd
- Rows: 100; enabled: 92; disabled: 8
- Expected V2 classification: 21 candidate_staged; 79 manual_review

## Reviewed row changes

| Row | Company | Previous classification | Current classification | Decision |
|---|---|---|---|---|
| 2 | Mistral AI | Lever mistral | Ashby mistral.ai | Stage corrected Ashby candidate; official Mistral careers page is provenance |
| 13 | SoundHound AI | Greenhouse soundhoundinc | Generic official careers page | Manual review; do not guess another ATS slug |
| 36 | The Standard | Manual / Workday adapter gap | Workday candidate | Stage review-only; V2 supports the Workday candidate normalizer |
| 43 | Caxton Associates | Manual / Workable adapter gap | Workable candidate | Stage review-only; V2 supports the Workable candidate normalizer |

The manifest's verified_* labels are source evidence, not V2 live verification. All imported candidates remain low-confidence and unlinked.

## Safe import and stale-candidate handling

The V2 importer is pinned by both source ref and SHA-256. The import is atomic and idempotent. It only writes manifest audit rows and unmatched global ATS candidates.

After this branch is reviewed, merged, and deployed under the normal release gates:

1. Run the Company Watch dry-run first. It must report 100 rows, 21 candidates, 79 manual-review rows, and the exact SHA-256 above.
2. Import using the admin-only Company Watch import endpoint.
3. Confirm the ten production registry boards and ten schedules are unchanged; confirm zero new employer records, zero linked/verified/active boards, zero new schedules, zero network requests and zero notifications from the import.
4. Find the old candidate by provider/key lever/mistral and reject it through the admin-only global-candidate review endpoint. Current production candidate ID: 1.
5. Find the old candidate by provider/key greenhouse/soundhoundinc and reject it through the same endpoint. Current production candidate ID: 6.
6. Confirm the new ashby/mistral.ai candidate exists as discovered; SoundHound must have no ATS candidate from this manifest row.
7. Do not link, verify, activate, or schedule any of these candidates as part of this correction.

Use provider/key rather than hard-coded IDs when performing the review; IDs can change if other candidates are imported first. The two IDs above are only the current production observations.

## Explicit non-goals

No production database write is part of this PR. No direct SQL patching, board activation, source allowlist changes, polling changes, search API integration, recurring discovery worker, Telegram, or member-feature work is included. The production 24-hour source reliability window remains a separate acceptance gate.