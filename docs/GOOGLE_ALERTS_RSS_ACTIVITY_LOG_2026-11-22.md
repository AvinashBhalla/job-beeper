# Google Alerts RSS — activity log and end-to-end audit

**Activity date:** 22 November 2026
**Working branch:** `feat/google-alerts-rss-atom-parser`
**Branch base at audit start:** `4393b1b` (`origin/feat/google-alerts-rss-atom-parser`)
**Status:** Engineering proof-of-path passed in isolation; live pilot relevance, baseline handling and recurring operation remain open. **Not approved for production.**

This file records the work performed on 22 November, the evidence actually obtained, the distinction between fixture testing and live-feed results, and the remaining gates. It intentionally does not contain private Google Alerts feed URLs, feed credentials, or full private feed identifiers.

## 1. Executive status

The RSS parser and safe-publisher-fetch components are testable, and a verified posting can be normalized into JobBeeper's existing shared job and member-evaluation paths. The end-to-end platform test was performed in a disposable database using a real public Shine posting page and a representative **synthetic RSS queue entry**.

That test does **not** prove that either of the currently configured live pilot feeds has delivered a job posting. The read-only pilot database shows:

- OpenAI pilot: HTTP 200, 20 Atom entries persisted, all 20 still `queued`. The inspected results are predominantly news, social posts and other non-job content.
- JavaScript Developer pilot: HTTP 200, zero entries persisted.
- Both feeds last succeeded at `2026-11-22T09:37:44Z` (15:07:44 IST). No ETag or Last-Modified values are stored for either feed.
- No matching systemd timer was found for Google Alerts/RSS. The implementation currently offers a one-shot batch entry point, not a recurring service.

Therefore: **the code-to-matcher path is demonstrated; the live job-discovery use case is not yet accepted.** Do not migrate or change any of the owner's existing email alerts based on this test.

## 2. Work completed

### 2.1 Feed parsing and regional Google URL support

Reviewed the current Atom parser and polling implementation and added regional Google India support:

- Google `google.co.in` redirect wrappers are recognized by the URL unwrapping helper.
- The feed poller's explicit allowed-host list now includes `google.co.in` and `www.google.co.in`.
- Added regression tests for regional redirect unwrapping and the regional feed host.
- Existing handling remains bounded: Atom parsing, stable entry IDs, Google redirect unwrapping, response-size and content-type checks, conditional request support where validators exist, persisted error/backoff state, and idempotent entry persistence.

The private feed URLs are held outside the repository. The pilot database stores opaque feed IDs/labels and parsed results, not feed URLs.

### 2.2 Publisher-page extraction improvements

Reviewed the extraction output against a live public posting:

**Fixture posting:** [Software Engineering - React & Node - Associate (India), PwC Acceleration Centers in India](https://www.shine.com/jobs/software-engineering-react-node-associate-india/pwc-acceleration-centers-in-india/20106180)

The safe public-page fetch succeeded with HTTP 200. The extracted JobPosting included:

- Title and hiring organization.
- Location: `All India, IN`.
- Published date: `2026-11-20T05:04:06+00:00`.
- Employment type: `FULL_TIME`.
- A description of approximately 4,876 characters.
- A valid publisher-page URL on `www.shine.com`.

The original extractor discarded the JSON-LD `skills` array. Added bounded, de-duplicated extraction of structured JobPosting skills and explicit `experienceRequirements`.

The publisher page did not provide experience requirements in the captured JobPosting JSON-LD or description. The representative Google result snippet contained `0 to 4 Yrs`. Added strict parsing for a single unambiguous range (or plus-years value), with a separate provenance value:

- JSON-LD `experienceRequirements`: `employer_stated`, high confidence.
- Google Alerts result snippet: `search_result_metadata`, medium confidence.
- Ambiguous or missing evidence: remain unknown.

The snippet is retained as lower-trust source evidence; it is not presented as employer-authored description text. The structured experience requirement takes precedence over snippet metadata.

### 2.3 Matcher integration

Updated the existing matcher to read source metadata from either the normalized `source_details` object or serialized `source_details_json`.

The matcher now considers explicitly published JobPosting skills even when they are not repeated in the description. Experience extraction can use validated structured JobPosting evidence and the separately marked Google Alerts snippet evidence.

Incremented `MATCHER_RULES_VERSION` from 3 to 4 so persisted evaluations can be recomputed under the changed matching rules. Kept `EXPERIENCE_EXTRACTION_VERSION` at 1; a temporary bump to 2 was reverted after it broke an existing baseline-migration assertion.

### 2.4 Regression coverage

Added tests for:

- Google India redirect and feed host handling.
- Structured JSON-LD skills with duplicate removal.
- Explicit JobPosting experience requirements.
- A single unambiguous Google result-snippet experience range.
- Ambiguous snippet rejection.
- Experience provenance priority.
- Matching structured skills absent from the job description.
- Passing snippet experience into matcher evaluation.

## 3. End-to-end proof and exact boundaries

### 3.1 What was actually exercised

1. Fetched the real Shine publisher page through the safe public-fetch helper (HTTP 200).
2. Captured that page's HTML as a local test fixture.
3. In a disposable, network-disabled application container, inserted a representative **synthetic** Google Alerts Atom queue row pointing at that Shine page.
4. Passed the captured page to `process_google_alert_rss_queue()` through its injected fetcher.
5. Invoked the actual `radar.normalize_job()` and `radar.upsert_jobs()` functions.
6. Verified the resulting shared `jobs` row, canonical opportunity and evaluation.
7. Created a synthetic member and saved preferences in that same disposable database, then verified its `user_job_evaluations` record.

### 3.2 Recorded result

| Check | Result |
|---|---|
| Queue item claimed | 1 |
| Verified JobPosting | 1 |
| Inserted into shared jobs table | 1 |
| Rejected / blocked / needs review / retryable | 0 |
| Canonical opportunity | Created |
| Member match | `True` |
| Member match score | 82 |
| Member experience evidence | 0–4 years |
| Candidate experience in fixture profile | 2 years |
| Member reasons | India location; Software Engineering title family; React and Node skills; experience compatible |
| Notification ledger | `pending` in scratch DB |
| Telegram delivery worker | Not invoked; 0 sends |

The job row included the source, title, company, destination URL, location, posted date, experience range and provenance, and source details. The sample profile used India, Software Engineering, React, Node and 2 years' candidate experience.

**Important boundary:** the safe page fetch was exercised against the live publisher separately; the application-container queue-to-upsert test used the captured HTML through an injected fetcher. The RSS queue item itself was a synthetic fixture. This was not a live Google feed entry flowing end-to-end.

## 4. Field coverage for member filters

| Field | Evidence / current state |
|---|---|
| Job title | Extracted from verified JobPosting; used by title/role matching |
| Company | Extracted from hiring organization |
| Publisher/application URL | Resolved and stored |
| Location | Extracted from JobPosting; sample returned `All India, IN` |
| Skills | Extracted from structured JSON-LD and description; structured skills now included in matching |
| Experience | Employer-stated structured requirements where provided; otherwise an unambiguous result-snippet range with medium confidence |
| Posted date / freshness | JobPosting date captured; usable by existing freshness logic |
| Employment type | Captured in source details, but not currently a dedicated member preference/filter |
| Remote/workplace type | Existing JSON-LD location/telecommute extraction support when publisher data supplies it |
| Salary | No normalized salary extraction/filter demonstrated |
| Industry | No dedicated normalized industry extraction/filter demonstrated |

Existing member preference fields include target roles, locations, skills, candidate experience, minimum/maximum job experience, match threshold, title exclusions, excluded role terms, remote-only mode and maximum job age. The test exercised role, location, skills and experience. Do not imply that employment type, salary or industry are already member-selectable filters.

## 5. Live pilot database — read-only audit

The pilot SQLite database was opened in read-only mode. No feed was polled and no row was changed during this inspection.

| Feed label | Last HTTP status | Consecutive failures | Persisted entries | Entry processing state |
|---|---:|---:|---:|---|
| Temporary OpenAI RSS pilot | 200 | 0 | 20 | 20 queued |
| JavaScript Developer job-alert pilot | 200 | 0 | 0 | No entries |

The 20 OpenAI results include social posts, news, videos and other non-job pages. This is evidence that Atom ingestion and persistence work for that feed response, not evidence that it is a relevant job source. No entries have been attempted by the publisher-page processing worker in this pilot database.

Both feeds last checked successfully at **15:07:44 IST on 22 November 2026**. Neither stored an ETag or Last-Modified validator. A later recurring poll and feed-entry retention comparison has not been demonstrated.

A read-only systemd timer search found no matching Google Alerts/RSS recurring timer. The current batch entry point is manually callable and one-shot.

## 6. Test and validation results

| Validation | Result |
|---|---|
| Focused RSS + safe-fetch + extraction + pipeline + matcher suite | **81/81 passed** after the experience-version correction |
| Radar regression module | **191/191 passed** after the correction |
| Python compilation for changed source and test modules | Passed |
| `git diff --check` | Passed |
| Full V2 discovery attempt | 494 tests discovered; not a clean full-suite pass |

The full V2 discovery attempt was run in an offline disposable container. It initially reported one failure because the temporary experience-version bump changed an existing migration expectation; the version bump was reverted and the subsequent 191-test radar module passed.

The full discovery attempt also had eight environment-related errors: FastAPI TestClient tests could not import because `httpx2` is absent from the selected image, and two tests require DNS/network resolution while the container was deliberately run with `--network none`. The full 494-test discovery run was not repeated with those external prerequisites. Do not describe the entire V2 suite as green.

The selected application image was used only as a throwaway, network-disabled test runtime with a separate scratch database. Production containers, production database, notifications, and deployment were not modified.

## 7. Remaining release gates

1. **Live relevance gate:** produce at least one genuinely job-related entry from a pilot feed and verify the result against its publisher page. The current OpenAI pilot is noisy; the JavaScript Developer pilot has zero entries.
2. **First-sync baseline:** distinguish old entries present at initial subscription from new entries. Do not turn the initial feed backlog into a notification burst.
3. **Recurring worker:** configure a conservative scheduler, durable checkpoints, retry/backoff, health reporting and a queue-draining worker. A one-shot batch call is not recurring ingestion.
4. **Queue completion:** prove all eligible entries are processed in bounded batches, including queues larger than one batch, without losing work or repeatedly refetching completed entries.
5. **Field-quality sampling:** test several publishers/ATS platforms, location formats, company naming conventions, skills representations, remote jobs, missing experience and expired listings.
6. **Filter completeness:** decide whether employment type, salary and industry are product requirements for member filters; they are not presently demonstrated as normalized member preference fields.
7. **Deduplication and notification dry-run:** verify feed-to-feed and cross-source canonical deduplication, per-member matching, initial baseline behavior and notification eligibility without sending.
8. **Full regression / CI:** run complete V2 tests with the declared test dependencies and required network fixtures/controlled DNS, then validate the feature branch CI. The current local results are not a substitute for that gate.
9. **Feed inventory reconciliation:** repository planning documents refer to 98 alerts; the owner's latest report says 103. Confirm the authoritative count before scaling or importing the full configuration.

## 8. Owner action required

**No immediate owner action is required.** Keep the existing email alerts unchanged. Do not move the wider alert set to RSS yet.

When the technical gates are ready, the owner will need to confirm the current alert count (repository documentation says 98; the latest owner report says 103) and approve any change to delivery mode. No feed URLs need to be pasted into this activity log or committed to Git.

## 9. Working-tree and production status

- Work remains on `feat/google-alerts-rss-atom-parser`.
- At audit start, branch HEAD and origin-tracking HEAD were both `4393b1b`.
- The extraction, pipeline, RSS host support, matcher and test changes were local uncommitted work. The activity log and next-agent handover update are being added to this same feature branch.
- No code was merged to `v2-live-radar`.
- No production service, production database, production config, existing email alert, scheduler or notification setting was modified.
- No Telegram/email notifications were sent.
- The feature remains **not production-ready** until the release gates above pass.

## 10. Recommended next execution order

1. Add first-sync baseline semantics and tests before any notification path can consume the initial entries.
2. Build and test the recurring poll/queue-drain worker with observable per-feed status and conservative cadence.
3. Diagnose why the JavaScript Developer feed returned zero and validate the OpenAI pilot's relevance; use a separate controlled, job-specific alert/feed if necessary without modifying the owner's existing email rules.
4. Capture at least one real job entry from the pilot and run it through live safe fetch, extraction, upsert and per-member evaluation in an isolated DB.
5. Run duplicate, baseline, stale/expired, 403/429, robots-denied, retry and multi-member tests.
6. Complete full V2 regression and branch CI; only then prepare a separate production release plan.
