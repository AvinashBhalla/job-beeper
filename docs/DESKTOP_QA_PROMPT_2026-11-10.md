# ChatGPT Desktop browser QA — persistent ATS board scheduler

## Owner setup (before running the prompt)

The candidate is the isolated container `job-radar-board-scheduler-qa`, listening only on `127.0.0.1:18011`, with volume `job-radar-board-scheduler-qa-data`. It is not the normal dev/QA/prod service. Notifications are disabled. Current accounts count was zero at the 2026-11-10 handover checkpoint.

Create the isolated QA admin and member interactively from an SSH terminal on the VM. Do not put passwords in command-line arguments, environment variables, scripts, shell history, this repository or ChatGPT messages. The CLI prompts for passwords without echoing them:

```bash
sudo docker exec -it job-radar-board-scheduler-qa python -m v2.auth_admin create-admin --email qa-admin@jobbeeper.test
sudo docker exec -it job-radar-board-scheduler-qa python -m v2.auth_admin create-user --email qa-member@jobbeeper.test
```

Create the admin first, then the member. Use unique strong test passwords and keep them in a password manager. If either account already exists, do not delete or reset it; check the current DB/account status and use the existing owner-known credentials.

Open the private internal site created for the candidate and sign in to the Termalin account if prompted. The owner should manually enter the app credentials when the browser reaches the app login screen. Do not ask for passwords in the report or include credentials in screenshots.

## Desktop agent prompt

You are acting as an independent QA engineer. Test the running JobBeeper candidate through the browser only. Do not edit code, change configuration, activate/deactivate boards, scan/discover employers, verify boards, trigger manual polls, save preferences, alter notifications or mutate any application data. Do not access production, normal dev or connector-QA. Test only the candidate at the URL opened by the owner.

### 1. Establish environment and baseline

- Confirm the address is the isolated candidate dashboard at the Termalin internal site, not another JobBeeper environment.
- Open the dashboard and record the candidate version, page title and visible dashboard navigation.
- Confirm the dashboard loads without a blank screen, persistent loading state, authentication loop or unhandled browser error.
- Ask the owner to manually sign in as `qa-admin@jobbeeper.test`. Never request, copy, log or report the password.

### 2. Admin scheduler panel and API

- Navigate to the admin-only Source Health section and locate **Persistent employer-board scheduler**.
- Verify the page shows a per-board table and a separate shared API-host budget table.
- As an admin, request `GET /api/discovery/scheduler/status` using the authenticated browser session. Do not copy cookie values or tokens into the report.
- Record the HTTP status, response timing and safe response fields. Confirm the API returns 200 and includes `active_boards`, `inactive_boards`, `max_concurrent_hosts`, `max_concurrent_boards_per_host`, `host_min_interval_seconds`, `boards` and `hosts`.
- Expected seed: 10 active boards across eight providers and seven API hosts; maximum three concurrent hosts, one active board per host, five-second host spacing. Current exact run counts/jobs may have increased since this seed; read actual values instead of hardcoding stale counters.
- Expected board set: Ashby/OpenAI; Ashby/PostHog; Darwinbox/Arvind; Greenhouse/Coinbase; Greenhouse/Graviton Research Capital; Greenhouse/Zocdoc; Keka/Bridgestone; SmartRecruiters/Bosch Group; Workable/Hugging Face; Workday/NVIDIA.
- Verify UI board rows match the API's active board records. Check provider, company, board key, API host, 3,600-second cadence, next due time, last result, jobs seen/new, failure count and baseline state.
- Verify UI host rows match the API host records. Check active lease, next allowed time, cooldown, 429 count and last outcome. An active lease should display as running; otherwise show idle.
- Check dates render as valid IST times, not `Invalid Date`, `NaN` or blank values. Verify the status summary reports three concurrent hosts, one board per host and five-second host spacing.
- Confirm the response does not include API credentials, auth tokens, request payloads, private endpoint URLs or full board config secrets.
- Refresh the dashboard and confirm the state is still rendered from persisted data.
- Verify other existing Source Health elements (provider table, coverage information and Workday inventory details) have not disappeared or been broken by the new panel.

### 3. Role-based access checks

- Log out of the admin account through the UI.
- Ask the owner to manually sign in as `qa-member@jobbeeper.test`; do not request or record the password.
- Confirm the member cannot see or navigate to the admin-only Source Health/scheduler panel.
- Attempt `GET /api/discovery/scheduler/status` from the member browser session. Expected: HTTP 403 (or the app's documented admin-denied response), with no scheduler details returned.
- Attempt existing admin-only source-health/discovery read routes only as read-only GET requests. Expected: 403, not data leakage.
- Log out, then make one unauthenticated GET to `/api/discovery/scheduler/status` in a clean/incognito session. Expected: 401.
- Do not attempt any write endpoints during this QA pass.

### 4. Responsive and interaction checks

Test these viewport sizes using browser responsive tools:

- Desktop: 1440 × 900
- Laptop: 1024 × 768
- Tablet: 768 × 1024
- Mobile: 390 × 844
- Narrow mobile: 320 × 740

At every size:

- Check the page has no unintended horizontal overflow; wide tables may scroll inside their own table container but must not push the whole page sideways.
- Check headings, summary text, badges, table cells and controls remain readable and do not overlap, clip or disappear.
- Check the scheduler table can be inspected horizontally on narrow widths.
- Check Source Health tabs/navigation remain usable and do not cover the last table row or controls.
- Use keyboard Tab/Shift+Tab to reach navigation and interactive controls; focus must remain visible.
- Check the live status text/summary remains readable and does not cause layout jumps.

### 5. Browser diagnostics and safety

- Inspect browser console and network requests throughout the test.
- Record uncaught exceptions, failed assets, failed API calls, mixed-content/CORS errors, repeated request loops and unexpected 5xx responses.
- Treat the expected member 403 and anonymous 401 checks as expected results, not defects.
- Do not treat third-party ATS requests made by the backend as browser failures unless surfaced to the UI as errors.
- Do not send notifications, trigger a manual source run, or alter application state.

### 6. Evidence and report

Create a Markdown report named `JOBBEEPER_SCHEDULER_DESKTOP_QA_2026-11-10.md`. Save it in the Desktop QA working folder and return the complete report in the conversation. Attach screenshots or a screenshot index where possible. Never include passwords, cookies, CSRF tokens, session IDs or other secrets.

Use this structure:

1. Environment and timestamp (include timezone); confirm candidate URL/port and that it is not production.
2. Test summary: PASS / FAIL / BLOCKED counts.
3. Admin scheduler endpoint: HTTP status, response latency, active/inactive board counts, board rows, host rows and comparison with UI.
4. Board-by-board table: provider, board, latest outcome, due time, failures, baseline and PASS/FAIL.
5. Host-by-host table: host, lease state, next allowed time, cooldown, 429 count and PASS/FAIL.
6. Member and anonymous authorization results with actual HTTP codes.
7. Responsive matrix for all five viewport sizes.
8. Console/network findings with exact route/status and timestamp; separate expected 401/403 from defects.
9. Screenshots/evidence filenames and what each proves.
10. Bugs with severity (P0/P1/P2/P3), concise repro steps, expected vs actual, and screenshot/console evidence.
11. Final recommendation: ACCEPT, ACCEPT WITH FIXES, or BLOCKED. Do not mark acceptance if admin/member accounts were not tested or if evidence is missing.

Do not fix any bugs. Return evidence and recommendations only so the engineering agent can make and document changes separately.
