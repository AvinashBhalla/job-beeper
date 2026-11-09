# Keka portal resolution — implementation plan

**Date:** 2026-11-09 19:30 IST  
**Branch:** feat/global-ats-discovery-hirebase-guard-20261109  
**Status:** implemented in the current worktree; focused and full V2 regression passed; not yet pushed or deployed.

## Finding from source research

The current Keka collector fetches the employer careers HTML, extracts a public document/feed identifier, then always calls /careers/api/embedjobs/default/active/{feed_id}. This is only correct for a default Keka portal.

The researched ats-scrapers adapter accepts public URLs with either:
- https://{tenant}.keka.com/careers (portal = default)
- https://{tenant}.keka.com/careers/{portal-slug} (portal = lowercase path segment)

It uses the resolved portal in both /careers/api/organization/{portal}/careerportalinfo and /careers/api/embedjobs/{portal}/active/{identifier}. The existing JobBeeper config already requires an employer name, so an organization metadata request should be optional rather than added to every 120-second collection cycle.

Reference code: https://github.com/kalil0321/ats-scrapers/blob/main/src/ats_scrapers/scrapers/keka.py and tests/test_keka.py.

## Implementation plan

1. Add one shared safe Keka portal parser in board_discovery, with strict HTTPS host validation, no credentials/nonstandard ports/query/fragment, exactly one or two path segments, required first segment careers and a safe second-segment slug.
2. Keep default portal behaviour unchanged for /careers URLs.
3. For non-default paths, use the actual portal slug in the embed-jobs endpoint and include it in source_details and source_job_id to avoid cross-portal identity collisions.
4. Construct the posting URL under /careers/{portal}/jobdetails/{job_id} for non-default portals; preserve /careers/jobdetails/{job_id} for default.
5. Use the same resolver in board verification so a candidate cannot verify against one portal and then be collected through another endpoint.
6. Reject unsafe/ambiguous deeper routes (including reserved paths such as api, applyjob, content and jobdetails) rather than guessing.
7. Do not call the portal-info endpoint on every poll. Company name is already configured; portal-info can be used for controlled verification or when a company label is missing.
8. Preserve existing redirect same-host validation, response-size cap, request telemetry and 429 cooldown.

## Tests required

- default /careers uses portal default and existing endpoint/URL contract remains unchanged;
- non-default /careers/ebenezerschool uses portal-specific embed endpoint and job-details URL;
- another non-default portal slug is independent and uses its own source_job_id namespace;
- malformed slugs, extra path segments, reserved route names, off-host redirects and unsafe URLs fail closed;
- verification probe and collection use the same resolved portal;
- member role cannot access admin board verification or status endpoints;
- default Keka board source flags remain disabled and there are no new live network requests in tests.

## Acceptance

At least two distinct non-default mocked public portal paths can be verified and collected, while the default portal remains backwards compatible. No global company discovery claim should be made: portal URL discovery is a separate P0 task.
## Implementation status — 2026-11-09 19:47 IST

Implemented in the current worktree. The strict resolver supports default `/careers` and non-default `/careers/{portal-slug}` paths. Non-default board keys use `tenant:portal`; job IDs include tenant and portal. Collector and verifier both use the portal-specific embed endpoint and job-detail URL. Config allows distinct portals on one tenant and rejects duplicate tenant+portal. Focused tests: 37 passed. Full V2 regression: 439 passed in 359.301 seconds. Keka changes are pushed in afa177b; exact-head GitHub V2 CI #1431 passed.
