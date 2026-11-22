# Google Alerts Gmail — Activity Log and Deployment Preparation

**Checkpoint:** 22 November 2026 (UTC)

> Chronological audit log. Entries are appended as work proceeds; older sections record their state at the time and may be superseded. The newest OAuth acceptance/deployment state is in the final section and `GOOGLE_ALERTS_GMAIL_LIVE_ACCEPTANCE_HANDOFF_2026-11-22.md`.
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

## 22 November 2026 — approved configuration wiring and safe preflight

1. The owner reported that Google approval had been received for the intended single-owner personal Gmail workflow. The approval correspondence remains private and is not copied into the repository. Scope remains exactly one owner account, `gmail.readonly`, the `JobBeeper/GoogleAlerts` label and Gmail history polling.
2. Added the dedicated Gmail environment mapping to `v2/docker-compose.yml`: client ID/secret, localhost callback, owner user ID/email, Fernet encryption key, polling mode/interval and live-access flag. Defaults remain `polling`, 180 seconds and `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false`.
3. Added `v2/google_alerts_gmail_preflight.py`. It loads and validates private Gmail settings, requires localhost polling mode without Pub/Sub, and checks via SQLite read-only mode that the configured owner ID belongs to an active administrator. It makes no OAuth/Gmail/Telegram requests and performs no DB writes. It never prints secret values.
4. Added four preflight tests for valid active admin binding, non-admin rejection, missing-owner rejection and the live-off guard. Focused regression: **35 tests passed, zero failures** across the new preflight suite, Gmail integration and Gmail radar modules. The four new preflight tests raise previously established unique coverage from 620 to **624 test cases**; the 34-module broad regression result remains a distinct, previously completed run. Python compilation, dashboard JS syntax, `git diff --check` and YAML parsing for all three Compose files passed.
5. Clarified that `.env.feature` and `v2/docker-compose.feature.yml` are not the Gmail deployment path; the feature stack is a disposable demo with a separate DB and does not pass these settings.
6. Remaining configuration inputs are not installed in the isolated checkout: dedicated Gmail OAuth client ID/secret, JobBeeper owner admin ID and Fernet key. The existing member-login OAuth client must not be reused. A private environment file must be configured in the actual deployment, followed by the read-only preflight.
7. No real OAuth request, Gmail mailbox read, Telegram external send, Pub/Sub provisioning, production DB migration, container restart, deployment or live-access activation was performed.


## 22 November 2026 — owner private environment validated

1. Verified /home/ubuntu/job-beeper/.env metadata only: mode 600, owner ubuntu:ubuntu. The nine Gmail variable names are present and their values are non-empty/non-placeholder. No credential or key value was displayed.
2. The isolated branch's google_alerts_gmail.load_config() accepted the private values, confirmed the Fernet key format, exact localhost callback, polling mode/180-second interval, no Pub/Sub configuration and JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false.
3. A read-only query inside v2-radar-1 verified that the configured owner ID maps to an active administrator in the production DB. No email address or account ID was output.
4. docker compose --env-file /home/ubuntu/job-beeper/.env -f v2/docker-compose.yml config --quiet passed against the feature-branch Compose file.
5. Critical release-path distinction: the currently running service uses /var/backups/job-radar-daily/release-dda6d57-20261118T2210IST/candidate-compose.yml and that directory's root-owned ./runtime.env. That runtime file has no Gmail keys and the running container has no JOB_RADAR_GMAIL_* variables. The owner .env is ready to be explicitly supplied to the reviewed feature-branch Compose file with --env-file; it has not been loaded into the running container. Do not mutate the archived release bundle's runtime env or restart the service as a workaround.
6. No deployment, container restart, Gmail OAuth, mailbox access, token creation, Gmail sync, or Telegram external send took place. Live access remains disabled.


## 22 November 2026 — production Compose contract and hosted check audit

1. Reviewed the exact running deployment definition. It binds the service only to 127.0.0.1:8000, reads a root-only runtime env file, and mounts external Docker volume v2_radar-data.
2. Hardened the feature-branch production Compose file to preserve that binding and volume explicitly, retain the current cookie/public-origin settings, pass the Gmail variables from the owner-controlled private env file, and use a versioned candidate image tag job-radar-prod-release:gmail-20261122.
3. Revalidated Compose with the real private env file using config --quiet; no interpolated credentials were printed. This preflights configuration only and does not modify/recreate the running container.
4. Inspected the latest exact-head GitHub Actions V2 CI run for 5efa631. It failed before any job steps (steps=[]); the log artifact was not available. It did not execute the test suite. No rerun was requested. Local focused regression and full historical offline coverage remain the available test evidence.
5. No production backup, image build, container restart/deployment, Gmail OAuth, mailbox read, or Telegram send has happened yet.


## 22 November 2026 — deployed login/consent fixes and Google OAuth audience blocker

### Engineering fixes and deployment

1. Owner confirmed creation of the Gmail label `JobBeeper/GoogleAlerts`. The intended filter configuration was then instructed, but its completion was not explicitly confirmed; verify it before the first successful sync. The owner then opened the production dashboard through SSH local forwarding to `http://localhost:8080`.
2. The first dashboard login returned `403 Cross-origin login is not allowed`. Root cause was Docker source NAT: the browser request came from `localhost`, but the container saw bridge gateway `172.18.0.1`. PR [#103](https://github.com/AvinashBhalla/job-beeper/pull/103), commit `ee44e7af1deec7a923b007a5ccc568a2a1542f1a`, added a narrow localhost/no-forwarded-header allowance and regression coverage. The 5 focused Gmail/radar tests passed. The fix was deployed as `job-radar-prod-release:originfix-20261122`; the owner then signed in successfully.
3. On the Account panel, the consent POST initially returned 422 and the UI displayed `[object Object]`. Root cause: shared `dashboard/auth.js` passed a plain object as the fetch body rather than JSON-serializing it. PR [#104](https://github.com/AvinashBhalla/job-beeper/pull/104), commit `8c25ff8b13d6ed4a25ac8f2caa79e73a5373cb29`, added JSON body serialization, the JSON content type, retained CSRF handling and formatted FastAPI validation details. Dashboard contract suite: **12 passed**. The candidate image also passed the 5 Gmail/radar tests and Python compile checks. The fix was deployed as `job-radar-prod-release:gmail-consent-20261122`.
4. Both app updates recreated only `v2-radar-1`, retained the external `v2_radar-data` volume, preserved the loopback-only `127.0.0.1:8000` port and current Gmail live-access env setting, and passed health/dashboard/OpenAPI HTTP 200 checks. Fresh root-only SQLite backups were created before each deploy; latest is `/var/backups/job-radar-daily/release-gmail-consent-20261122T062255Z`, checksum-verified, SQLite integrity `ok`, with 28,731 jobs and 2 users.
5. The running container currently has `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=true`. This is a configuration gate only; it does not mean a mailbox is connected. Do not change this value as part of the Google test-user fix.

### Google OAuth attempt and observed blocker

1. After the frontend fix deployed, the browser consent POST returned **200 OK**, and `GET /api/integrations/google-alerts/gmail/connect` returned **302 Found**. Thus the browser/client and JobBeeper consent route worked.
2. Google then returned **403 `access_denied`**. The page says JobBeeper has not completed Google's verification process and is in testing, accessible only to developer-approved testers.
3. Request details visible in the screenshot: `access_type=offline`, scope `https://www.googleapis.com/auth/gmail.readonly`, `response_type=code`, redirect `http://localhost:8080/api/integrations/google-alerts/gmail/callback`, PKCE `S256`, prompt `consent`.
4. This is a Google OAuth audience/test-user allowlist blocker, not an application CORS or consent-payload problem. The exact Gmail account used for authorization must be listed under the same OAuth project's **Google Auth Platform → Audience → Test users** if the project is External/Testing. First confirm the selected Cloud project owns the client ID configured on the VM. Do not switch app type, broaden scopes, or publish Production as a workaround.
5. Google policy research confirms `gmail.readonly` is a Restricted scope. External/Testing projects allow up to 100 test users and test authorizations expire after seven days. Restricted-scope production verification and potential server-side security assessment remain separate gates. A limited-personal-use or test-user grant must not be mistaken for full production OAuth verification or a CASA/security assessment.

### Read-only production state after the failed Google authorization

- `google_alerts_gmail_credentials=0`.
- `google_alerts_gmail_data_use_consents=1` (one consent row from the latest connect attempt; inspect `consumed_at`/expiry rather than assuming the consent is reusable).
- `google_alerts_gmail_oauth_states=1` (an OAuth attempt/state row; no code returned to callback).
- `google_alerts_gmail_messages=0`, `google_alerts_gmail_sync_state=0`, `google_alerts_gmail_opportunities=0`.
- SQLite `PRAGMA integrity_check=ok`; jobs remain 28,731.
- No Gmail refresh token, granted mailbox credential, message body or sync/backfill was created. No callback request was observed in the app logs.

### Next owner action

Open the exact Google Cloud project associated with the configured Gmail OAuth Web client. In Google Auth Platform → Audience, check user type and publishing status. If External/Testing, add the exact Gmail mailbox account used for the Google Alerts label to Test users and Save. Then retry through the same localhost tunnel, re-check the disclosure, and connect using that allowlisted account. If it still fails, capture the new exact error and verify project/client/account pairing. After a successful redirect, validate owner identity and label, then confirm encrypted credentials and sync state. Do not enable Telegram as part of this test.

The authoritative step-by-step handoff, current runtime image, test-mode limitations and policy references are in `docs/GOOGLE_ALERTS_GMAIL_LIVE_ACCEPTANCE_HANDOFF_2026-11-22.md`.


## 22 November 2026 — first successful Gmail authorization and backfill

1. Owner added two Google developer-approved test accounts and subsequently completed the Google OAuth flow. The dashboard now reports initial backfill complete and incremental history reconciliation active.
2. Read-only production verification: 1 encrypted Gmail credential; 4 Gmail messages all `processed` with no error codes; 8 parsed alert results; 1 Gmail-derived historical opportunity; one sync row with `backfill_state=complete`, label binding and incremental history cursor; no sync error. SQLite integrity `ok`; jobs count 28,732 (prior pre-Gmail count 28,731).
3. The sole retained Gmail job is **Software Engineering – React & Node – Associate** at **PwC Acceleration Centers in India**, location `All India, IN`. The current evaluation reports `match=0`, `score=0`, reason `location outside configured targets`. No preferences were changed.
4. No Telegram chat is linked to the owner; no notification setting or notification ledger row exists. The Gmail owner is an administrator. The current dashboard hides Telegram linking for admins and the Telegram/link/notification APIs reject admin accounts. Record this as a product integration gap: implement an owner-admin Telegram link and explicit opt-in path, rather than attempting to link a second Gmail tester or changing the owner binding.
5. The owner confirmed label creation earlier; creation/application of the Gmail filter to future and historical matching conversations still needs explicit confirmation. Incremental Gmail history polling is active; continue processing only the configured label.
6. No Telegram account was linked, no notification was enabled, no Telegram message was sent, and no target-location preference was altered.
7. Next: owner verifies the retained job in the feed and decides whether `All India` belongs in saved location preferences; verify the Gmail filter; implement owner-admin Telegram opt-in if desired; keep delivery gated by current matching, freshness, private-chat linking and explicit opt-in. Google Testing authorizations remain temporary, and Restricted-scope production/policy assessment gates remain applicable.

See `GOOGLE_ALERTS_GMAIL_LIVE_ACCEPTANCE_HANDOFF_2026-11-22.md` for current totals and implementation details.


## 22 November 2026 — Telegram owner-admin path deployed; webhook registered

1. The owner reported that the three new role-based Google Alerts had been created. Settings were As-it-happens, Web only, English, India, All results. No new email from these new alerts had yet been confirmed. The `JobBeeper/GoogleAlerts` label exists; confirm that the Gmail filter is saved/applied to existing and future conversations.
2. PR [#107](https://github.com/AvinashBhalla/job-beeper/pull/107) (`e9e521a93aa19f76f92f9b7d25c2440004604066`) introduced a narrowly scoped Telegram owner-admin exception: only the authenticated administrator whose ID equals `JOB_RADAR_GMAIL_OWNER_USER_ID` can view/use Telegram APIs. All other admins remain blocked; members retain existing behavior. Dashboard panel is now shown only after server authorization succeeds.
3. Added tests for owner-admin private chat linking, no enable before link, explicit enable after private link, unlink disabling notifications, denial for other admins, dashboard visibility and admin preference re-evaluation. Three focused new tests passed; the complete user-preferences API module exited 0. Dashboard auth-contract + user-notification delivery tests + focused admin CSRF regression: **42 passed**. Static JS syntax, Python compilation and `git diff --check` passed.
4. Fixed the admin `/api/config` preference save to schedule evaluation refresh for the first active admin after synchronizing admin preferences. This prevents existing job evaluations from retaining a stale preferences fingerprint. After deployment, the existing PwC Gmail job location now matches `All India, IN`; its score is **44**, but the reason `no configured target-role match` remains, so it is not eligible for notification.
5. Validated existing bot via Telegram `getMe`; bot username is `Qdhorvbot`. Added `JOB_BEEPER_TELEGRAM_BOT_USERNAME=Qdhorvbot` and a new `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET` to the private `/home/ubuntu/job-beeper/.env`, preserving owner `ubuntu:ubuntu` and mode `0600`. No secret value was displayed or committed.
6. Read-only TLS check confirmed public HTTPS reachability at the VM IP, IP SAN in the Let's Encrypt certificate and automatic certbot renewal timer. Registered Telegram webhook `https://130.210.27.197/api/telegram/webhook` for `message` updates only, 5 max connections, no pending-update drop. Telegram `setWebhook` returned success; `getWebhookInfo` verified exact URL, zero pending updates and no last error. This enables the private `/start` link handshake; it does not send job notifications.
7. Candidate image `job-radar-prod-release:telegram-owner-20261122` (`sha256:69385fb40ca2d93a4a101d01484c8c25f1a030083366bfe0bb5f7230b2486834`) built from merged PR #107. Production Compose config passed `config --quiet`; candidate loaded the private Gmail/Telegram settings correctly and Python 3.12 compile checks passed. Candidate image does not include dev-only `httpx2`, so API tests were executed in the isolated host test venv instead.
8. Fresh pre-deploy backup: `/var/backups/job-radar-daily/release-telegram-owner-20261122T074641Z`. Root-only mode 0700, files 0600, checksums verified. SQLite integrity `ok`; 28,734 jobs, 1 Gmail credential, 0 Telegram chats and 0 enabled notification settings.
9. Deployed by recreating only `v2-radar-1` with the candidate image. Preserved loopback-only `127.0.0.1:8000` binding and external volume `v2_radar-data`. `/health`, `/dashboard/`, `/openapi.json` returned HTTP 200; restart count 0; OOM false. The admin Telegram JavaScript is present in the served dashboard assets.
10. Post-deploy read-only DB: jobs 28,734; Gmail credential 1; 4 historical messages processed with 8 parsed results and no errors; Gmail backfill complete and incremental history active; 0 Telegram chats; 0 enabled notification settings; 0 notification ledger rows. No job-alert Telegram message was sent.
11. Owner next action: hard-refresh JobBeeper, open Preferences/Settings, generate the one-time link, open it in a private chat with `Qdhorvbot` and press Start, then refresh connection status. Keep job notifications off until the owner explicitly opts in. Resolve `Software Engineering` role-title equivalence/match threshold before expecting the currently imported PwC job to qualify. Wait for a first email from new Google Alerts and confirm the Gmail filter labels it before declaring the new query pipeline accepted.

See `TELEGRAM_OWNER_ADMIN_SETUP_HANDOFF_2026-11-22.md` for current UI instructions, safeguards, production runtime and full next steps.

## 22 November 2026 — Telegram start-button diagnostic and legacy-delivery correction

1. Owner opened the generated `t.me/Qdhorvbot?start=...` link in Chrome. Screenshot remained on Telegram's web landing page with a **START BOT** button and did not open the private chat.
2. The `/api/telegram/link` API had succeeded at 08:05:03 UTC. Read-only DB checks found one unconsumed/unexpired owner link token with a 10-minute TTL. No `/api/telegram/webhook` POST was observed after link creation. Telegram `getWebhookInfo` continued to report the exact registered webhook URL, zero pending updates and no last error. This points to Chrome not handing the `tg://` deep link off to Telegram Desktop/mobile, not a broken app webhook.
3. Recommended workaround: open Telegram Desktop or mobile directly; search `@Qdhorvbot` / Jobwatcher; open its private chat; send `/start <payload>` using the actual value after `start=` in the still-valid generated link. Bare `/start` does not consume the account-link token. Regenerate from JobBeeper if the 10-minute link expires. After delivery, check `/api/telegram/webhook` logs and refresh dashboard connection status.
4. Important correction to the rollout note: the new owner-specific account is still unlinked and `user_notification_ledger` is empty, but the **legacy global notifier is enabled** (`JOB_RADAR_TELEGRAM_CHAT_ID` and bot token are configured; app `notifications_enabled=true`). Log lines show two legacy LinkedIn notifications delivered at 07:51:58 UTC and one at 07:57:37 UTC on 22 November. This old sender uses a fixed global chat ID and does not depend on `user_telegram_chats` or per-user opt-in. It was left untouched. Do not claim that no Telegram job alerts were sent; distinguish this old global channel from the new owner-specific per-user channel. Ask before disabling the old global notifier.

## 22 November 2026 — owner chat linked and per-user opt-in switched on

1. Owner reported successful Telegram connection. Production DB confirms one private Telegram chat linked to the configured Gmail owner admin. Latest successful webhook POST: 08:21:58 UTC (13:51:58 IST).
2. The owner notification settings API received PUT /api/notifications/settings and returned HTTP 200 at 08:22:13 UTC (13:52:13 IST). Read-only DB enabled_at is 2026-11-22T08:22:13.655197+00:00; the explicit “Send matching new-job alerts to my connected Telegram chat” setting is ON.
3. Per-user notification ledger remains empty (0 records, 0 pending), as no new eligible job has qualified. The current PwC Gmail job remains score 44 and match=0 because there is no configured target-role match. Per-user alerts only consider jobs discovered after the enabled timestamp; historical Gmail backfill is not automatically sent.
4. Gmail remains at 4 processed historical messages, 8 parsed results, all history_backfill=1; there are zero messages with history_backfill=0. Initial backfill is complete; incremental history reconciliation remains active and has no error. First new email from the recently created Google Alerts remains outstanding.
5. The separate legacy global Telegram notifier is still configured/enabled and had sent three LinkedIn alerts after rollout (2 at 07:51:58 UTC, 1 at 07:57:37 UTC). These use the pre-existing static global chat configuration and do not appear in the owner per-user notification ledger. This legacy path was not modified.
6. Next: confirm Gmail filter applies the dedicated label; validate next new email end-to-end; ensure any candidate was discovered after the per-user opt-in timestamp and passes all matching/freshness/public-post checks; then verify one queue record and delivery. Do not use historical backfill or the non-matching PwC row as a send test.

See TELEGRAM_OWNER_ADMIN_SETUP_HANDOFF_2026-11-22.md for current operational state and remaining acceptance checks.

## 22 November 2026 — first-email wait diagnosis and Spam-folder findings

1. Read-only Gmail API query for authenticated Google Alerts sender googlealerts-noreply@google.com over the last 7 days returned 6 messages: 4 inbox messages with the JobBeeper label and 2 Spam messages without it.
2. Full metadata (From, Subject, Authentication-Results) was checked with the application's own is_google_alerts_metadata validator. All six messages passed. Four inbox/label emails were received on 20 November at 19:48:55, 19:49:10, 20:49:18 and 22:05:00 IST. Two Spam emails were received on 20 November at 19:29:24 and 20:29:26 IST. Neither Spam email carried the selected JobBeeper label.
3. All six messages predate the new role-based Alerts created on 22 November. There are no authenticated Google Alerts messages received on 22 November as of this checkpoint. Thus there is no new email yet for JobBeeper to ingest; do not blame the app's history poller.
4. JobBeeper still has 4 historical messages processed, 8 parsed results, zero errors. Label-scoped history reconciliation is polling every 180 seconds; latest poll at 14:02 IST, no error and no new history events. Per-user Telegram opt-in remains ON from 13:52:13 IST but queue remains empty because there are no new history events.
5. Next owner action: edit the existing Gmail filter for googlealerts-noreply@google.com, retain label JobBeeper/GoogleAlerts, add Never send it to Spam, and do not select Also apply filter to matching conversations to avoid backfilling the two old Spam emails as new label events. Add the sender to Contacts. Then verify the three alerts remain enabled and wait for a message received after the filter change.
6. The new-email acceptance chain is still pending: sender authentication, label, ingestion, public posting verification, target-role/skills/location/score/freshness match, and one per-user Telegram delivery. No settings or scopes were changed during this check.

See TELEGRAM_OWNER_ADMIN_SETUP_HANDOFF_2026-11-22.md for dates, counts and exact owner actions.
