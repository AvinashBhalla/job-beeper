# Product Reverse-Engineering Plan

**Status:** Discovery and evidence-gathering phase  
**Updated:** 2026-11-05  
**Working repository:** [AvinashBhalla/job-beeper](https://github.com/AvinashBhalla/job-beeper)  
**Active branch:** `v2-live-radar`

## Goal

Build a personal job-intelligence system that continuously discovers jobs from a broad set of permitted job-board, ATS and employer-career sources; normalizes and deduplicates the results; evaluates them against a personal candidate profile; and delivers fresh matches through Telegram and a dashboard. A separate referral-intelligence subsystem should identify relevant people using authorized sources, enrich professional contact details where permitted, prepare personalized messages and manage human-approved outreach.

The future hiring-post stream (recruiter/employee posts that announce openings) is explicitly later scope. Do not mix it into the first job-ingestion release.

## Research targets

1. **JobBeeper:** observable product pages, filters, job cards, freshness/discovery labels, company pages, source coverage, notification behavior, frontend bundles, and browser-visible network activity.
2. **Uplers HAPPPY:** job input, company/team identification, people discovery, contact enrichment, relevance ranking, personalization, Gmail consent/sending, LinkedIn permissions, review controls and follow-up tracking.
3. **Existing Job Radar V2:** code, tests, branch state, runtime configuration, source health, timestamps, matching, notification ledger, deployment and rollback path.
4. **REA:** use [morluto/rea](https://github.com/morluto/rea) for passive CDP website observation and offline HAR inspection. Do not treat it as a private-backend source extractor or an unrestricted browser automation tool.

## Initial repository findings (2026-11-05)

- Inspected branch head: `ef73b3c8bee77b14c4b0ebd7ac319ab7cf94fc7a` on `v2-live-radar`.
- Latest V2 CI run on the exact head: [#40651863587](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651863587), conclusion `success` (2026-10-28). This does not establish VM deployment.
- Older `main` head: `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; continue V2 work from `v2-live-radar`.
- Collectors currently registered: LinkedIn, Naukri, Instahyre, Greenhouse and Ashby.
- Tracked `v2/config.json`: LinkedIn and Naukri enabled; Instahyre, Greenhouse and Ashby disabled. Tracked development config: Naukri only, notifications disabled. Runtime `/data/config.json` can override tracked production configuration.
- LinkedIn has 16 tracked fast-lane query/location targets (4 queries × 4 locations) and scans up to 2 targets per 180-second cycle. Under uninterrupted success, a complete first-page rotation is nominally 24 minutes. This is a scheduling estimate, not a measured live p50/p90.
- LinkedIn requests are globally paced at 4 seconds, use a 25-second request timeout, and honor HTTP 429 with global escalating backoff (300-second base, 1,800-second cap, Retry-After respected).
- Observability gap: `/api/source-status`, `/api/latency-summary` and `/api/dedupe-candidates` currently omit Ashby although it is registered as a collector. Confirm and test the intended behavior before fixing.
- The tracked `source_state.json` is an old snapshot, not live runtime health.
- No source was triggered, no code/config was changed, and no Oracle operation was performed during this audit.

## Evidence standards

For each product claim, record:
- **Observed:** directly seen in the product, browser, a publicly accessible endpoint or an authorized account flow.
- **Inferred:** a plausible explanation, clearly labeled and tied to supporting evidence.
- **Unknown:** private implementation details, unavailable workflows or unverified claims.

Never claim to know a vendor's private backend implementation based only on its UI or public marketing. Reconstruct observable product behavior using independent implementation choices.

## REA and browser setup

1. Check Node.js and npm versions. REA currently requires Node 22.23.4+, 24.22.1+ or 26.12.1+.
2. Run `npx rea-agents@latest setup`; review the exact configuration plan and approve only the intended coding agent.
3. Restart that agent after setup.
4. Start a separate Chrome profile with a debugging endpoint bound only to `127.0.0.1`; do not expose CDP to LAN or public internet.
5. Use REA's passive browser tools to capture page structure, resources, scripts, console/network metadata and screenshots.
6. Use Chrome DevTools to save HAR with content when needed; inspect offline with REA.
7. Redact cookies, authorization headers, bearer tokens, secrets, inbox contents, personal contact details and other sensitive payloads before sharing captures.
8. Stop the dedicated browser after the investigation.

## Oracle runtime audit — read-only gate

Before any deployment or code change, establish:
- exact branch, commit and git working-tree state of production and development checkouts;
- container name, image/revision and compose project;
- mounted SQLite volume and effective runtime configuration without printing secrets;
- source enabled flags, last run/success, request counts, error classes, 429/cooldown state and per-source job yield;
- source posting timestamp precision, discovered timestamps and measured latency;
- match/evaluation/notification-ledger/Telegram timestamps.

Do not run job-processing endpoints simply to generate sample data. Do not print environment variables, API keys, config tokens, Telegram credentials or session material. Preserve local uncommitted files and volumes. No restart or pull until branch/runtime state is reviewed.

## Planned deliverables

1. JobBeeper evidence report and behavior map.
2. HAPPPY evidence report and permission/integration map.
3. Existing-system audit and measured latency diagnosis.
4. Source/provider matrix (coverage, timestamp quality, permissions, freshness, API limits, cost and terms).
5. Master architecture and separate PRDs for source ingestion, matching, notifications, referral intelligence and later hiring-post discovery.
6. Test and rollout plan with explicit freshness, dedupe, alert consistency, source isolation and rollback gates.

## Explicit non-goals for the initial phase

- No private SaaS backend extraction or authentication bypass.
- No LinkedIn proxy/account rotation, CAPTCHA bypass or policy-evading automation.
- No automatic LinkedIn connection requests or messages; use official authorized integrations if available, otherwise require human action.
- No expensive provider subscription until a controlled sample demonstrates added coverage, freshness or accuracy.
- No ground-up rewrite before the existing V2 audit is complete.
