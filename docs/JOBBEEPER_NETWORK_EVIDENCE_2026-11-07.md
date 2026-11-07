# JobBeeper network evidence — 2026-11-07

## 1. Executive summary

**OBSERVED:** JobBeeper serves /user/jobs as a document and then fetches job data in the browser. The list request is GET /api/user/jobs with numeric page, page-size, status, sort, and keyword-search parameters.

**OBSERVED:** Next-page navigation changed page=1 to page=2; this is page-number pagination, not a cursor or infinite-scroll request.

**OBSERVED:** Ten idle one-minute observations saw no JobBeeper Fetch/XHR, WebSocket, or SSE-style traffic. This covers only the observed window, not all possible refresh cadences.

**OBSERVED:** Opening a detail produced separate metadata and tracker GETs, plus a normal UI view-marking POST.

## 2. Test environment and investigation window

**OBSERVED:** Dedicated user-authenticated Chrome profile; REA attached through loopback Chrome DevTools Protocol. Scope remained limited to JobBeeper normal browser activity.

**OBSERVED:** Initial load, pagination, detail, and search were captured around 17:40–17:44 IST. Ten consecutive idle one-minute observations ran around 17:44–17:54 IST.

**OBSERVED:** No cookies, authorization values, header values, request bodies, response bodies, or storage values were retained.

## 3. Initial feed-load observations

**OBSERVED:** GET /user/jobs returned HTTP 200 as the document. Relevant HTTP 200 browser fetches then included:

- GET /api/auth/user/me
- GET /api/user/jobs/companies?page=1&limit=50
- GET /api/user/jobs/filters
- GET /api/user/jobs/stats
- GET /api/user/notifications/summary
- GET /api/user/trial-offer
- GET /api/user/jobs?page=1&per_page=20&status=matched&sort_by=created_at&sort_order=desc

**OBSERVED:** One document load completed in about 94 ms; initial static assets commonly completed in roughly 80–315 ms.

**INFERRED:** The document supplies the application shell while the job list is populated by a browser fetch, because the list request followed the document request.

**UNKNOWN:** Response body schemas, payload sizes, and field names; bodies were intentionally not retained.

## 4. Background refresh observations

**OBSERVED:** Across ten idle one-minute capture windows, no JobBeeper Fetch/XHR response, WebSocket creation, or SSE-style event was observed.

**UNKNOWN:** A longer polling cadence, a push mechanism inactive for this account state, or another refresh mechanism outside the selected event families.

**OBSERVED (UI):** The account displayed a subscription-expired message stating that the feed is delayed six hours and real-time notifications are paused. This is UI text, not proof of backend refresh design.

## 5. Filter/search observations

**OBSERVED (UI):** The expanded filter UI exposes Companies, Roles, Experience, Source / ATS Sources, notification status, and sort controls, alongside Search jobs.

**OBSERVED:** Entering java in Search jobs caused this request (HTTP 200):

GET /api/user/jobs?page=1&per_page=20&status=matched&sort_by=created_at&sort_order=desc&search=java

**INFERRED:** Keyword search is server-side for this action, because the browser issued a new list request with search.

**UNKNOWN:** Exact parameter names/values for the other visible controls; they were not individually applied in this run.

## 6. Pagination/infinite-scroll observations

**OBSERVED (UI):** The feed displayed Previous/Next and Page 1 of 16.

**OBSERVED:** Next generated GET /api/user/jobs?page=2&per_page=20&status=matched&sort_by=created_at&sort_order=desc (HTTP 200).

**INFERRED:** Conventional server-side numeric pagination with a visible requested size of 20.

**UNKNOWN:** Response fields for totals, page count, or next-page state.

## 7. Job-detail observations

**OBSERVED:** Opening /user/job/28889972 produced:

- GET /api/user/jobs/28889972/metadata — HTTP 200
- GET /api/user/jobs/28889972/tracker — HTTP 200
- POST /api/user/jobs/28889972/view — HTTP 200

**OBSERVED:** The detail action also fetched the notifications summary.

**INFERRED:** Some detail-associated data is loaded separately from the list request.

**OBSERVED (UI):** Feed cards expose title, company, location, displayed datetime, experience with provenance, source, match score, skills, and work-arrangement/other labels where available.

## 8. Source labels and timestamp semantics

**OBSERVED (UI):** Source labels included LinkedIn, Ashby, Naukri, Lever, and Hirist.

**OBSERVED (UI):** Cards distinguish Employer-stated experience from From description experience. They show absolute datetimes, for example Nov 7, 2026, 1:23 AM.

**UNKNOWN:** Whether displayed dates mean original posting, discovery, ingestion, refresh, or display time.

## 9. Sanitized request inventory

| Request | Method | Status | Observed purpose |
| --- | --- | --- | --- |
| /user/jobs | GET | 200 | Jobs document |
| /api/auth/user/me | GET | 200 | Authenticated bootstrap |
| /api/user/jobs | GET | 200 | Paged job list |
| /api/user/jobs/filters | GET | 200 | Filter-control data |
| /api/user/jobs/companies | GET | 200 | Company filter data (page, limit) |
| /api/user/jobs/stats | GET | 200 | Feed statistics |
| /api/user/notifications/summary | GET | 200 | Notification summary |
| /api/user/trial-offer | GET | 200 | Trial/offer state |
| /api/user/jobs/{id}/metadata | GET | 200 | Detail metadata |
| /api/user/jobs/{id}/tracker | GET | 200 | Detail tracking state |
| /api/user/jobs/{id}/view | POST | 200 | Normal detail-view action |

## 10. Observed vs inferred vs unknown

- **OBSERVED:** Numeric page parameters, per_page=20, status=matched, newest-first sorting, and server-requested keyword search.
- **INFERRED:** The list is browser-fetched after the shell document; page controls use numeric server pagination.
- **UNKNOWN:** API response schemas, timestamp semantics, source-filter values, polling beyond ten minutes, and private ingestion architecture.

## 11. Implications for Job Radar

1. Preserve value provenance: distinguish source-reported from description-derived values, including confidence.
2. Instrument list, filter, stats, and detail requests separately instead of treating feed render as one operation.
3. Record page, size, sort/filter state, returned count, duplicates, and freshness markers per collector run.
4. Report Job Radar as five concrete adapters (LinkedIn, Naukri, Instahyre, Greenhouse, Ashby); keep Greenhouse/Ashby coverage employer-board based.
5. Track distinct source-posted, first-seen, last-successful-check, and last-material-change timestamps.

## 12. Recommended next experiments

1. Apply Companies, Roles, Experience, Sources, and notification status one at a time; record only changed parameter names and HTTP outcomes.
2. Use a safely redacted test account or fixture to document response field names without retaining account-specific payloads.
3. Repeat passive refresh observation over a longer window and an active subscription state.
4. Compare stable IDs between pages for overlap and deduplication behavior.
5. Open two more source-diverse details and compare only sanitized request shapes.

## Evidence references

- Passive page: ev_060117c58632640276b8e8ad5c4413d26bde65e615a4ca16f9e64b35bb6ed00f
- Initial feed: ev_bc7f649d1ee2f46573b0218a4e5119d07b63ba96b2f3a7ffe956f3ab24c3b066
- Pagination: ev_2e975c22bd9b0d273d96d8ad26ce706d063d6b77f40ccefd1dff6e4c42b2d0b9
- Detail: ev_4b90fe8361e122e47318825936108f305f03e99e914eba3c636b23b551071939
- Search: ev_0d534928b96a352adf29ad7a39c893219fd334c0dd5ee19c43ea6362cd0535c7
