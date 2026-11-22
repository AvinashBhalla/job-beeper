# Google Alerts Gmail — Activity Log and Deployment Preparation

**Checkpoint:** 22 November 2026 (UTC)
**Repository:** `AvinashBhalla/job-beeper`
**Feature branch:** `feat/google-alerts-gmail-ingestion`
**Draft PR:** [#102](https://github.com/AvinashBhalla/job-beeper/pull/102)
**Isolated checkout:** `/home/ubuntu/job-beeper-google-alerts-dev`

## Executive status

The no-domain personal Gmail route is implemented in the isolated feature checkout: localhost OAuth callback through an SSH local-port-forward tunnel, followed by periodic Gmail history polling (180-second default). No custom domain, public callback endpoint, Gmail `users.watch`, Pub/Sub topic/subscription, or paid GCP resource is required for this mode.

**This is preparation only, not a deployment.** Production remains on image `job-radar-prod-release:dda6d57`, container `v2-radar-1`, bound to `127.0.0.1:8000`, with external volume `v2_radar-data:/data`. The production container was inspected read-only and its `/health` endpoint returned `status=ok`. No production container, database, configuration, Nginx, OAuth grant, or Telegram delivery was changed.

## Activities completed on 22 November 2026

1. Confirmed the owner's preference: personal single-account use, no domain purchase, no Pub/Sub provisioning, no multi-user Gmail product work.
2. Updated Gmail synchronization to support polling mode without `users.watch`. The initial profile history cursor is captured before backfill; initial catch-up is reconciled; later `users.history.list` work is paginated and bounded per worker pass. A stale history cursor causes a fresh baseline/full resynchronization.
3. Adjusted worker pacing so queued messages or incomplete incremental-history pages are drained promptly instead of sleeping for the full poll interval. Polling defaults to 180 seconds and remains configurable from 60 to 3600 seconds.
4. Added localhost SSH-tunnel login-origin handling. The non-Secure cookie exception is restricted to direct HTTP requests to `localhost` arriving from loopback with no forwarded proxy headers; normal public/proxied requests retain Secure cookies. No global cookie-security downgrade was made.
5. Updated `.env.feature.example`, `docs/GOOGLE_ALERTS_GMAIL_INBOX_INTEGRATION_2026-11-21.md`, and `docs/NEXT_AGENT_START_HERE.md` to describe the personal polling path and exact callback/tunnel settings.
6. Re-ran the complete V2 regression after these changes: **all 34 test modules passed, 616 tests, zero failures**, in nine bounded local batches (107, 28, 51, 53, 49, 191, 42, 26 and 69 tests). The Gmail-focused batch passed 53 tests and the broad radar module passed 191. Python compilation for `v2/google_alerts_gmail.py` and `v2/radar.py` and `git diff --check` passed. No hosted CI was used.
7. Read-only VM inspection confirmed the application listener on `127.0.0.1:8000`; `/health` returned `{"status":"ok","version":"2.0.0"}`. Read-only `sudo docker ps` confirmed `v2-radar-1` running `job-radar-prod-release:dda6d57` and `sudo docker inspect` confirmed the mounted external volume `v2_radar-data:/data`.
8. Read-only Docker labels identified the active Compose project `v2`, working directory `/var/backups/job-radar-daily/release-dda6d57-20261118T2210IST`, Compose file `candidate-compose.yml`, service `radar`. Read-only Nginx inspection confirmed public proxy requests receive `X-Forwarded-For` and `X-Forwarded-Proto`; these headers prevent a public request with a spoofed `Host: localhost` from qualifying for the direct-loopback cookie exception.
9. Inspected only the release-bundle file names and a redacted Compose view. The bundle contains a prior production SQLite snapshot (139,456,512 bytes) and runtime/config artifacts dated 18 November. It is historical evidence, **not** a fresh pre-deployment backup for a 22 November change.
10. Inspected `v2/docker-compose.feature.yml` and determined it is not suitable for this personal Gmail deployment: it is a demo/test container on port 8002 with a separate database, demo mode, global cookie-security override, and blank Telegram chat routing. Do not use it as the production personal-Gmail target.

## Current source-control state

- Branch: `feat/google-alerts-gmail-ingestion`.
- The tested Gmail polling, localhost OAuth and initial disclosure implementation was published in commit `62989e8e2bbfc7c5642ee1a8ce724eb04c00a3e1`.
- Docs-only follow-up commit `b805d7f9c46d60643e9fb2779a8920bb9ddc73ee` followed that implementation commit. The present consent-hardening changes supersede that checkpoint; read the current PR #102 head rather than treating any SHA in this activity log as a live pointer.
- Before this follow-up, the isolated checkout was clean and tracking the remote feature branch. Re-check its current commit and status before running tests or making further edits.
- The commit contains 13 files: Gmail polling and localhost OAuth implementation, dashboard data-use disclosure/unchecked consent gate, regression tests, feature environment example, policy assessment, user data guide, activity log, and updated integration/handover documentation.
- PR #102: https://github.com/AvinashBhalla/job-beeper/pull/102. GitHub readback before this consent-hardening follow-up confirmed it was **open, draft, unmerged and mergeable**, targeting `v2-live-radar`. Re-read the live PR head and state before any review, merge or release action.
- No GitHub Actions workflow was triggered; the owner's hosted Actions quota remains a cost constraint.


## Exact tunnel after the feature is separately released

The current VM app listener is `127.0.0.1:8000`. Once the feature is deployed and the owner authorizes the connection step, run this from the owner's local machine and keep the SSH session open:

```bash
ssh -N -L 8080:127.0.0.1:8000 ubuntu@130.210.27.197
```

Open `http://localhost:8080` in the same local browser and configure this exact Google Web application redirect URI:

```text
http://localhost:8080/api/integrations/google-alerts/gmail/callback
```

Do not open the VM IP in the browser for this OAuth flow. The OAuth callback is `localhost` in the browser; SSH forwards it to the VM application. The tunnel must remain open through login and the Google consent callback.

## Deployment decision and blockers

**No deployment was performed or authorized by this activity record.** The user agreed to prepare a safe deployment, while the prior instruction explicitly retained deployment as a separate approval step.

Before any deployment:

1. The reviewed feature branch is committed and pushed at `62989e8e2bbfc7c5642ee1a8ce724eb04c00a3e1`; remote/local heads matched and the working tree was clean. PR #102 remains draft/open/unmerged. Do not mark it ready or merge until the policy and release gates are resolved. No paid GitHub Actions run was triggered.
2. Resolve Google's `gmail.readonly` Restricted-scope permitted-use-case, Limited Use/data-transfer, and server-side security-assessment applicability. The personal-use OAuth verification exception must not be represented as a blanket security-assessment waiver.
3. Agree on the exact deployment target and blast radius. The only live app currently identified is production `v2-radar-1` on port 8000; replacing it affects the existing JobBeeper service. The port-8002 feature Compose file is unsuitable. No isolated single-user deployment config has been prepared or validated yet.
4. Immediately before an approved release, take a fresh SQLite online backup from the live `v2_radar-data` database while the service is running. Record path, byte size, SHA-256, `PRAGMA integrity_check`, and key table counts. Do not use the 18 November release-bundle snapshot as the pre-deploy backup.
5. Preserve the active runtime environment file and current Compose file in place; never print secret values. Build an immutable candidate image from the exact reviewed commit. Keep `job-radar-prod-release:dda6d57` intact as the current rollback image. Prepare a new Compose release file that changes only the image tag and keeps the existing project, loopback port binding, external volume, and runtime environment unchanged.
6. Re-check the exact image, compose diff, DB backup, rollback image and health before applying. Recreate only service `radar` in project `v2`, and only after explicit approval for the production restart. Do not run `docker compose down`, remove/prune volumes, alter Nginx, or change source schedules/notification settings as part of this feature release.
7. After an approved release, verify health, dashboard, login, DB integrity/counts, existing source schedules/status, and that Gmail live access remains disabled until the owner completes Google setup and separately approves activation. Verify no external Telegram message is sent during deployment smoke tests.
8. Roll back by restoring the prior Compose image reference `job-radar-prod-release:dda6d57` and recreating only `radar`, preserving `v2_radar-data`. Restore a DB backup only for a confirmed schema/data problem, not merely an HTTP smoke-test failure.

## Explicitly not done

- No `docker compose build`, `docker compose up`, `docker compose down`, container restart, or image replacement.
- No DB migration, DB write, backup creation, or volume operation.
- No PR merge, mark-ready transition, or paid CI run. The feature branch commit/push was completed at `62989e8e2bbfc7c5642ee1a8ce724eb04c00a3e1`.
- No Gmail OAuth client/consent configuration, Gmail authorization, token storage, mailbox read, or live poller activation.
- No Pub/Sub, service account, billing, domain, DNS, certificate, Nginx, or public endpoint changes.
- No Telegram send or change to existing notification credentials/routing.

## Google policy assessment and user disclosure work — 22 November 2026

- Reviewed Google's Restricted Scope Verification page (updated 10 November 2026), Workspace User Data and Developer Policy (updated 22 July 2026), Gmail API scope reference, OAuth 2.0 Policies (last modified 5 August 2026), and Google API Services User Data Policy.
- Personal-use exception: the one-owner design appears eligible for the OAuth verification exception (creator-only/few personally known users). This is not a general policy waiver and users may still see an unverified-app warning.
- Unresolved permitted-use-case: Google lists email clients, backups, email productivity and user-benefiting reporting/monitoring that improves the email experience. JobBeeper's Alerts-to-job-discovery workflow is not explicitly listed; obtain Google's classification before the first live grant.
- Unresolved server-side assessment: the Gmail scope is Restricted and Google's policy says server-hosted access requires assessment. This backend is VM-hosted; conservatively assume CASA/security assessment applies unless Google confirms otherwise in writing.
- Code data-flow audit: raw MIME is fetched only after metadata/sender authentication checks and parsed in memory. The worker uses the extracted destination URL to fetch and verify a public JobPosting. Public job-page fields are stored as a private owner discovery; message-key digest, sync/processing metadata and Gmail-origin association remain. Their treatment as derived Google data requires Google's determination.
- Telegram is a third-party transfer and must be covered by a clear, separate affirmative user opt-in. Gmail connection must not enable Telegram notifications by itself.
- Added a detailed pre-connect data-use disclosure and initially unchecked confirmation to the Account panel. This follow-up adds a server-side, versioned consent ledger (Job Beeper user ID, disclosure version, accepted timestamp and one-time consumed timestamp). The OAuth-start endpoint rejects direct/replayed requests without unused current-version consent. Records remain after Gmail disconnect until account deletion; no Gmail content or credential is recorded in the consent ledger.
- Added a dashboard contract test proving the disclosure is present, Telegram is identified as a separate service, and the consent checkbox is unchecked by default.
- Added `docs/GOOGLE_ALERTS_GMAIL_USER_DATA_GUIDE.md` and `docs/GOOGLE_GMAIL_RESTRICTED_SCOPE_POLICY_ASSESSMENT_2026-11-22.md`. The help guide still needs a product-hosted public URL and the public privacy-policy/Limited Use statement remains outstanding.
- Validation after the dashboard disclosure change: 59 focused tests passed across the dashboard auth contract, Gmail parser, Gmail sync and Gmail/radar integration modules; `node --check dashboard/app.js`, Python compilation, and `git diff --check` passed. The full 616-test V2 suite had passed after the backend polling changes before this frontend/docs-only follow-up.
- Live Gmail remains disabled. Full assessment and remaining gates are documented in the policy file.

## Server-side consent-bypass fix — 22 November 2026

- Added disclosure version `2026-11-22-v2` and a consent ledger with an unused-consent uniqueness constraint. Each acceptance expires after 10 minutes; the OAuth-start transaction consumes only a current, unexpired acceptance. A schema migration gives older pending rows an already-expired default.
- Expired, unused attempts receive an `expired_at` audit timestamp. The partial unique index excludes expired records, so they remain as audit evidence without blocking a fresh acceptance.
- The dashboard now POSTs affirmative acceptance to the authenticated server before opening the OAuth URL. The OAuth-start GET atomically consumes the unused acceptance, so direct authenticated requests and replays are denied.
- The ledger stores only the Job Beeper account ID, disclosure version, acceptance time and consumed time. It survives Gmail disconnect as evidence and is removed by Job Beeper account deletion through the user foreign key.
- Added unit, API-route and dashboard contract coverage. Run the focused tests and record exact results before merge; no Gmail OAuth, mailbox access, Telegram delivery or production deployment is part of this change.

## Validation after server-side consent fix — 22 November 2026

- Focused regression: **3/3 passed**:
  - `GmailIntegrationTests.test_data_use_consent_is_owner_only_versioned_and_single_use`
  - `AuthApiTests.test_gmail_connect_requires_a_one_time_server_recorded_consent`
  - `DashboardAuthContractTests.test_gmail_connect_requires_explicit_data_use_confirmation`
- The API route test verified direct connect without consent returns 403, stale disclosure version returns 400, current acceptance returns 200, first OAuth-start request returns 302, and replay returns 403. Redirect following was disabled to keep the test offline.
- `node --check dashboard/app.js`, `python -m py_compile v2/google_alerts_gmail.py v2/radar.py`, and `git diff --check` all passed. The isolated worktree is clean and tracking the updated feature branch.
- A broader combined run of the Gmail, authentication and dashboard modules reached the local process execution deadline during a later dashboard contract test. No assertion failure was reported before the timeout. The consent-specific bounded rerun completed successfully; do not represent the timed-out command as a complete suite pass.
- No hosted Actions run was triggered.

## Current branch validation — 22 November 2026

- The broad bounded regression sweep passed **all 34 V2 modules: 619 tests, zero failures** in eight groups: 39 (6 modules), 56 (4), 54 (4), 104 (5), 191 (1), 81 (6), 59 (6) and 35 (2). The later disconnect cleanup regression added one test, bringing the unique coverage total to **620 tests**.
- After the final consent and disconnect changes on code commit `45b78edcadda6e5eb83c9cbbad1a26333eccb11d`, the Gmail and user-notification modules were rerun together: **55 tests passed, zero failures**. This covers the current `expires_at`/`expired_at` schema migration, expiry audit retention, fresh-consent retry, queued Gmail-only job cleanup and preservation of independent public jobs. The Google Alerts radar integration module also passed in the final preflight.
- Focused disconnect boundary regression passed: pending delivery rows for Gmail-only private jobs are removed by the job-deletion cascade; historical Gmail delivery rows attached to independently stored public ATS jobs are marked cancelled while public jobs remain.
- Focused consent/API/dashboard checks passed **3/3**: owner/version/single-use/expiry/re-consent; direct OAuth-start denial, one-time acceptance and replay denial; dashboard consent POST contract.
- Final preflight on the code candidate: `node --check dashboard/app.js`, Python compilation for Gmail/auth backend and tests, and `git diff --check` all passed. Documentation-only commits followed; refresh the isolated checkout and repeat the quick preflight before merge. The checkout was clean and tracking the GitHub branch at the time of validation.
- The earlier 616-test result is the pre-consent-hardening baseline. The broad sweep recorded 619 tests; the added disconnect lifecycle regression brings unique current coverage to 620 tests. Tests use synthetic fixtures in the isolated checkout. No hosted CI, real Gmail OAuth, mailbox read or Telegram send was used.

## Final post-change validation and review

- Historical pre-consent-hardening baseline: **34 V2 modules, 616 tests passed, zero failures**. The current consent-hardening regression is recorded in the section above.
- Batch results: 107 tests (6 modules), 28 (4), 51 (3), 53 Gmail-focused tests (4), 49 OAuth/shared tests (4), 191 radar tests (1), 42 (4), 26 (4), and 69 user application/notification/preferences tests (4). Total: 616 tests across 34 distinct modules.
- `py_compile` passed for `v2/google_alerts_gmail.py` and `v2/radar.py`; `git diff --check` passed after the code review.
- Final review covered the Gmail polling/push config and sync path, history cursor recovery, worker pacing, localhost origin/cookie boundary, push endpoint gating, regression tests, environment example and handover docs. No blocking issue was identified in the reviewed diff; no additional code change was made during this final review.
- The suite is offline synthetic validation only. Real Gmail OAuth/API, mailbox reads, live Telegram delivery, and production acceptance have not been performed.

## Next safe action

Obtain Google's determination on whether this job-alert-to-job-discovery use case is an approved Gmail-scope use and whether CASA/security assessment applies to the VM-hosted Restricted-scope backend. Resolve derived-data retention and any required encryption/storage controls, publish the public privacy-policy/help content and Limited Use statement, then review the implemented server-side consent record. Only then proceed to controlled live-mailbox acceptance under separate approval. Production deployment remains a distinct approval; before any release, take a fresh SQLite online backup and revalidate the release/rollback plan. Do not continue automatically into production deployment.

## Feature branch publication — 22 November 2026

- Committed the reviewed feature work as `62989e8e2bbfc7c5642ee1a8ce724eb04c00a3e1` and pushed `feat/google-alerts-gmail-ingestion` to `origin` successfully.
- Verified remote branch SHA equals local `HEAD`.
- Updated PR #102 title and description to reflect localhost OAuth, default polling, updated test results, and outstanding policy/consent/privacy gates. GitHub confirms the PR is still open, draft, unmerged and mergeable.
- No GitHub Actions run was triggered. No merge, production deployment, OAuth grant, live mailbox request, Pub/Sub, database write or Telegram send occurred.
