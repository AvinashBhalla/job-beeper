# Source-level ingestion metrics

**Status:** Implemented on `feat/source-observability-20261107`; draft PR #47.

**API:** Admin-only `GET /api/source-status`.

**Measurement window:** latest run plus rolling 24 hours.

## Scope

A common request instrumentation wrapper is used by the existing LinkedIn, Naukri, Instahyre, Greenhouse and Ashby collectors. The metrics layer records aggregate request metadata without storing endpoint paths, URLs, query parameters, headers, response bodies, job descriptions or credentials.

The wrapper does not change request cadence, concurrency, retry policy, source enablement, matching, notification delivery or external access methods. A retry that already existed in a collector is measured; this implementation does not add new retries.

## Metrics contract

| Metric | Meaning |
|---|---|
| `requests_attempted` | Physical HTTP GET attempts, including attempts made by existing retry loops and LinkedIn detail enrichment. |
| `responses_received` | HTTP responses returned by the client, regardless of status. |
| `request_exceptions` | Request exceptions that occurred before an HTTP response was available. |
| `http_2xx`, `http_3xx`, `http_4xx`, `http_5xx` | Response totals by status class. |
| `http_429` | Explicit HTTP 429 response count; also included in `http_4xx`. |
| `http_status_counts` | Exact response-code histogram, for example `{ "200": 12, "429": 2 }`. |
| `retry_attempts` | Physical requests marked as a retry by an existing collector retry loop. The initial request is not a retry. |
| `request_duration_ms_total` | Sum of elapsed milliseconds spent inside individual HTTP GET calls. It excludes caller-side LinkedIn pacing waits and retry backoff sleeps. |
| `avg_request_duration_ms` | `request_duration_ms_total / requests_attempted`; it is not end-to-end source-run duration. |
| `pages_attempted/succeeded/failed` | Logical feed/search pages. LinkedIn counts each search page; Naukri and Instahyre each count their feed fetch as one page. |
| `boards_attempted/succeeded/failed` | Configured employer-board fetches for Greenhouse and Ashby. These are board integrations, not global ATS indexes. |
| `jobs_seen` | Normalized jobs returned by the collector for that run. |
| `new_jobs` | New job rows inserted by the application during that run. |

## Run outcome semantics

- `success`: all measured logical pages/boards succeeded.
- `failed`: the collector raised an exception or every attempted logical page/board failed.
- `partial_failed`: at least one logical page/board failed and at least one succeeded; any usable returned jobs are retained.
- `rate_limited`: LinkedIn encountered a 429 with no usable jobs returned.
- `partial_rate_limited`: LinkedIn encountered a 429 after obtaining some jobs.

A recovered HTTP 503 followed by a successful retry can produce a successful run while the 503 remains visible in the status histogram and retry count. Partial results do not advance `last_success`; full successful runs do. Existing LinkedIn cooldown values and behavior are unchanged.

## Persistence and API

`source_runs` receives additive nullable fields for request counts, status-class counts, exact status histogram JSON, retry count, request-duration total, page counts and board counts. `_ensure_column` migrates existing databases without rebuilding or deleting historical run rows.

`GET /api/source-status` remains admin-only and keeps the existing `sources` response collection. Per-source additions:

- `last_request_metrics`: metrics from the latest run, or `null` when that run predates request-level instrumentation.
- `last_24h`: run totals, count of measured runs, request/status/retry totals, average request duration, page/board totals, job yield and failed/partial run counts.
- `http_status_counts`: rolling 24-hour exact status-code histogram.

`measured_runs` is deliberately included alongside total `runs`. Historical records with NULL metric fields are not converted to zero and must not be interpreted as measured data.

## Dashboard

The admin Source Health table displays 24-hour measured-run coverage, requests, HTTP 429s, retries, average request duration, and page/board failures alongside the latest job yield and last successful run. Historical periods with no instrumentation show **Not measured**. Partial failures are shown as **PARTIAL**, not as a total source outage.

## Privacy and operational safety

- Persist aggregate status codes and durations only; do not persist full exception strings, request URLs, query strings, request headers, response payloads, job descriptions or secret material.
- Disabled collectors stay disabled. LinkedIn pacing and existing retry behavior are unchanged.
- The instrumentation is safe to use as a diagnostic layer; it does not imply provider approval, source freshness or a real-time SLA.
- Source enablement, a collection-rate change, shared-dev rollout or production deployment requires separate review and approval.

## Validation

- Focused request telemetry, source status, migration, board/page outcome and 429 tests: **14 passed**.
- Full V2 unittest discovery: **199 passed** in 81.744 seconds on the isolated Python 3.10 test environment.
- `python -m compileall -q v2`, `python -m py_compile v2/radar.py v2/test_radar.py`, and `git diff --check` passed.
- The isolated metrics preview at remote loopback `127.0.0.1:8003` is seeded with clearly synthetic example rows and has every collector disabled and notifications off. It makes no external source requests. It is separate from the OAuth feature service on 8002, shared dev on 8001 and production on 8000.
- GitHub V2 CI #1307 / run `42391947214` passed for implementation commit `a9da22f92f9003e5317b8285fbcd5102ea348be9` on Python 3.12 and the current Node runner: dashboard JavaScript syntax passed, focused router/extractor tests **32 passed**, and the full V2 suite **199 passed in 27.721 seconds**.
- The VM's Node 12 is too old for the dashboard's existing modern JavaScript syntax; GitHub CI is the authoritative dashboard syntax check.
