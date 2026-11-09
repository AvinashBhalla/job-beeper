# Source Health & Coverage — Plain-English Guide and UX Redesign

**Owner feedback recorded:** 2026-11-09
**Applies to:** current production Source Health screen and next admin experience
**Status:** design recommendation; no production UI or API has been changed.

## 1. What this page is for

This page is an **operator control room**, not a job-match screen and not a single confidence score. It should answer five questions:

1. Are our source collectors running and enabled?
2. How many employer boards have we discovered, verified and activated?
3. When did each board last return successfully, and when should it be checked next?
4. Are requests failing, being rate-limited or falling behind?
5. Are the jobs we received still legitimate, current and traceable to the employer posting?

These are different questions and should not be combined into one ambiguous “confidence” number.

## 2. What the existing source table means

The current 12-column table contains measurements from source-run telemetry.

| Current label | Plain-English meaning | What it does **not** mean |
|---|---|---|
| Source | The provider/feed adapter: Workday, Keka, Darwinbox, Naukri, etc. | It is not one employer. One source may cover many employer boards. |
| Status | Whether the source is disabled, running, active, partially failing or failing. | ACTIVE does not prove that every employer using this ATS is covered. |
| Jobs Seen (Latest) | Number of listings returned in the most recent completed run. | Not lifetime jobs and not necessarily newly posted jobs. |
| New Jobs (Latest) | Number of new local records created in the latest run. | Not all jobs published in the last 24 hours; dedupe can make this zero even when the board was read successfully. |
| Measured Runs (24h) | Number of the last 24 hours' source runs that contain request telemetry, shown against total run count. | “Not measured” is missing historical telemetry, not zero requests. |
| Requests (24h) | HTTP requests attempted by the collector in the last 24 hours. | Not number of employers or jobs. |
| HTTP 429 (24h) | Count of rate-limit responses. The provider is telling the collector to slow down. | Not a generic server outage. |
| Retries (24h) | Retry attempts made after retryable request failures. | Not proof that the retry succeeded. |
| Avg Request (24h) | Average duration of an individual HTTP request, in milliseconds. | Not end-to-end posting-to-alert latency. It excludes discovery/index lag and may exclude processing/notification time. |
| Page / Board Failures (24h) | Failed page requests and failed employer-board checks compared with attempted totals. | A failed board does not necessarily mean all boards for that provider are down. |
| Last Success (IST) | Time of the latest successful source run. | Does not show how old the job postings themselves are. |
| Diagnostics | The last reported error/partial warning; Naukri also reports relay snapshot age and whether it changed. | Not a complete incident log or a user-facing job-quality score. |

### Why values can say “Not measured”

The API deliberately separates the historical count of runs from runs that have request telemetry. Older source-run records predate detailed request instrumentation. The UI should display “Not measured (historical run)” rather than silently display zero, because zero implies the system actually measured no requests.

### What ACTIVE means

ACTIVE is only a source-level enabled/idle state. It does not tell you:
- how many employer boards are found or currently monitored;
- whether every company using that ATS is discoverable;
- whether the next poll is due or overdue;
- whether new jobs are being found;
- whether the job is still open or a repost;
- whether a user profile matches the job.

The current screen does not calculate a “Source Confidence” score. It exposes operational telemetry. Board discovery confidence and job legitimacy/freshness are separate concepts.

## 3. The missing view: coverage by employer board

A provider row such as Workday hides the real scale dimension: employers/boards.

For example, one Workday adapter may know how to parse Workday jobs, but unless the system has discovered a particular employer's public Workday site and its tenant/cluster/site identifiers, it cannot fetch that employer's postings.

The replacement page should therefore show both:
- **Provider health:** is the Workday adapter functioning?
- **Board coverage:** how many public Workday employer boards are discovered, verified, active, pending, unavailable or stale?

The operator should not have to add each company manually in the normal workflow. The manual company form should move under “Add or correct a board manually” as an exception tool.

## 4. Proposed information architecture

### A. Top summary — answer “are we covering the market?”

Show four readable numbers with definitions and click-through:
- **Employer boards monitored** — verified boards currently scheduled.
- **New boards discovered (7 days)** — previously unknown boards found by discovery.
- **Sources needing attention** — provider or board runs that are overdue, failing or rate-limited.
- **Jobs newly captured (24h)** — unique job records first observed in the selected period, not total feed rows.

Do not label the total number of boards as market coverage percentage unless we have a defensible estimate of the total addressable employers.

### B. Coverage tab — answer “what have we found?”

Group by provider:
- provider name and collector support status;
- discovered boards;
- verified public boards;
- actively monitored boards;
- pending review;
- inaccessible/auth-required/blocked;
- stale boards not successfully checked within their expected interval;
- newest board discovery and most recent verification.

Clicking Workday should open the employer list, with each row showing company, career URL, country, evidence, confidence, last checked, last successful fetch and next poll.

### C. Freshness tab — answer “are we checking often enough?”

Use board-level status, not only source-wide timestamps:
- expected poll interval;
- last attempt;
- last successful poll;
- next due time;
- overdue age;
- latest job publication timestamp and its precision;
- last new job observed.

Keep provider publication time, employer update time, first seen by JobBeeper, and notification time separate. Unknown publication time must stay unknown.

### D. Reliability tab — answer “why did collection fail or slow down?”

Keep the existing engineering metrics but explain them:
- HTTP request count and response status distribution;
- 429 rate-limit count, Retry-After and active cooldown;
- retry attempts and outcome;
- average and p90 request duration (individual HTTP requests);
- page/board success ratio;
- latest error class and timestamp;
- historical runs with missing metrics clearly marked.

A 429 should say “Provider asked us to slow down; next retry scheduled at …”, not simply display a red badge.

### E. Job quality tab — answer “can I trust the captured listing?”

Keep this independent from provider health:
- official employer/ATS URL verified;
- application link present and on an acceptable host;
- structured employer-posted timestamp present and precision;
- board still lists the job on a later poll;
- last seen / last checked;
- closed, stale, repost or duplicate signals;
- source provenance and reason for a low/medium/high evidence label.

Do not score a job as legitimate merely because the HTTP request succeeded.

## 5. Recommended terminology and status logic

Use plain terms:
- **Monitoring** — board is active and scheduled.
- **Checking now** — a run is currently in progress.
- **Healthy** — last successful run within the board's expected interval and no current blocking cooldown.
- **Delayed** — last success is older than expected, but retry remains possible.
- **Rate-limited** — provider returned 429; display the retry/cooldown time.
- **Needs attention** — auth/robots/404/parser error or repeated failures need operator review.
- **Not monitored** — discovered or verified, but intentionally not activated.
- **Not enough data** — never checked or no valid timing sample.

Avoid using “confidence” for operational availability. Reserve discovery confidence for evidence that a URL belongs to a provider/employer, and job confidence for listing-level trust.

## 6. Acceptance criteria for a redesign

- An admin who is not an engineer can explain why a source is healthy, delayed or blocked.
- Each displayed metric has a short “what this means” explanation.
- “Zero” and “not measured” are distinguishable.
- Provider health and employer-board coverage are separate.
- A source can be ACTIVE while coverage is incomplete; the UI makes that obvious.
- Board-level last success and next poll are visible.
- 429s show the actual retry/cooldown state.
- Job legitimacy/freshness is shown per posting, not inferred from source uptime.
- Technical detail is collapsible/secondary; summary and action are primary.
- Member users do not see admin-only telemetry or company registry controls.
- API responses continue to enforce admin/authentication boundaries.

## 7. Recommended implementation sequence

1. Rename navigation to **Coverage & Health** and introduce a one-sentence explanation.
2. Add provider coverage counts using the existing board registry (discovered/verified/active/pending/blocked).
3. Add board-level last success and next due scheduling data; do not fake next-poll values from source-level intervals.
4. Redesign the table into summary + provider rows + expandable reliability detail.
5. Add a separate job-quality section after job legitimacy/repost signals exist.
6. Keep the old metric/API fields in the backend for compatibility while changing labels and presentation.
7. Test the admin view and member restrictions in separate authenticated contexts.

## 8. What is true today

The current page shows provider-level operational metrics and a per-company discovery form. It does not yet provide global ATS discovery, a comprehensive employer coverage index, board-level due scheduling, or per-job trust evidence. Those are engineering gaps, not user mistakes.
