# JobBeeper product plan

JobBeeper should help a user discover relevant openings, decide which ones to pursue, and track each application through follow-up. The current milestone is fetching only: grow a shared, continuously maintained job feed across public providers. Alert delivery, résumé work, and outreach follow once collection is established.

## Current milestone · Fetching and provider coverage

1. Validate the existing Greenhouse collector on a small set of boards relevant to India and remote roles. Suppress alerts for the first successful snapshot and persist new jobs from later polls. Compare title, employer, location and remote eligibility, skills, experience requirements and direct application link with the original posting. Preserve whether a field came from the employer or was inferred from the description.
2. Run the same ingestion checks across public providers in parallel. Grow the shared board catalog from employer career links, sitemaps, and public or licensed directories. Probe candidate boards before activation and review ambiguous employer associations. Add authorized aggregator feeds or platform alert emails as collection inputs if they contribute distinct, relevant jobs.
3. Keep provider collectors behind a common input contract and reuse the scheduler and normalized job records. Give frequently changing boards shorter intervals within host budgets. Use active coverage, unique relevant job yield, rate-limit responses, and discovery latency to prioritize the next connector.

For priority boards with reliable timestamps, the initial objective is p95 publication-to-discovery at or below 180 seconds. Report sample size and missing timestamps alongside percentiles. Backfill and date-only timestamps need separate interpretation.

### Initial Greenhouse pilot

The isolated dev pilot began with two-minute Greenhouse polls over Coinbase, Graviton Research Capital, and Zocdoc. Existing database state and initial-baseline suppression were retained. The dev instance has blank Telegram credentials.

Read the pilot window from the application's data volume using the deployment start time as the cutoff. The tool reads the existing database without changing it or delivering alerts.

```sh
docker exec job-radar-dev python -m v2.discovery_pilot --db /data/jobs.db --source greenhouse --since 2026-11-23T07:44:42Z
```

On 23 November 2026, development commit `5f62427` passed 48 focused tests on both Windows and the Linux VM, plus four baseline and database tests on Linux. Two live cycles each returned 252 Coinbase jobs, 20 Graviton Research Capital jobs, and 66 Zocdoc jobs. All six polls succeeded with zero new rows and zero HTTP 429s. The browser showed the existing feed, description-derived experience, direct links, and all three boards scheduled at 120 seconds. These cycles yielded zero publication-lag and Telegram delivery samples.

When a configured interval decreases, the scheduler now advances a healthy board's next due time from its last successful poll. The host request spacing, active leases, and failure cooldowns still apply. Verify the next checkpoint with a newly observed posting before assessing latency targets or promoting the pilot into a wider rollout.

### Multi-provider development rollout · 23 November 2026

The rollout uses the existing public provider adapters. Individual boards from the historical live-feed runbook, the attributed LastRound AI directory, and the Company Watch manifest were probed from the VM before scheduling. The development config sets a two-minute interval for seven Greenhouse boards, ten minutes for four Ashby, four Lever, two Workable, one Keka and one Darwinbox board, and twenty minutes for three SmartRecruiters boards. Each interval remains subject to the scheduler's host budget and backoff.

- Workday initially verified a public NVIDIA list page but the live scheduled poll returned HTTP 429. The Standard, Guidewire, and Autodesk also rate-limited probes. Workday is paused in development and NVIDIA's board and prior outcome are retained for later review. Deel's Ashby board returned an empty list at verification and was left out of the rollout.
- The Ashby validator and collector now agree on valid dotted board names, including Mistral AI. The focused provider and scheduler suite passed 74 tests on the Linux VM.
- The attributed LastRound AI snapshot added 9,935 unverified candidates covering Greenhouse, Ashby, and Lever. The separate 100-row Company Watch manifest staged 19 candidates and retained 81 rows for manual review. These imports do not schedule boards. Use the application's in-process admin import for future bulk batches. An import from a separate VM process overlapped initial collection and caused transient SQLite writer contention.
- If a collector fails and its error telemetry cannot be stored, the scheduler now releases the provider's running marker and can retry the board. The updated provider and scheduler suite passed 76 tests on the Linux VM. OpenAI recovered on a scheduled retry, and SmartRecruiters resumed after the deployment.

At 14:55 IST, all 22 active boards across seven providers had completed a successful scheduled poll and cleared their first-snapshot baselines. The development database had 4,653 canonical opportunities, up from 338 before rollout. Counts by source were Greenhouse 2,366, Ashby 1,307, Lever 409, SmartRecruiters 383, Keka 107, Darwinbox 41, and Workable 40. Repeated Greenhouse and Darwinbox polls completed, and no HTTP 429 responses were recorded for the seven active providers in this rollout window. The browser confirmed the expanded schedules and rendered newly ingested Lever postings. This snapshot establishes live fetching and ingestion; the added rows include existing employer inventory.

### Provider coverage and production promotion

Track parity with all 36 sources from the reference product's Delivery schedule. Integrations may use public employer feeds, approved partner feeds, or user-authorized alerts. Mark a source live only when a scheduled or event-driven run ingests a real posting, normalizes it, and handles a repeat without creating duplicate jobs.

| Status as of 23 November 2026 | Providers |
| --- | --- |
| Seven live on the development VM | Ashby, Darwinbox, Greenhouse, Keka, Lever, SmartRecruiters, Workable. Six also have successful recent production polls. Lever is the new provider in the development batch. |
| Four with existing adapters that need separate acceptance | LinkedIn, Naukri, Instahyre, Workday. LinkedIn is intermittently live in production. The Naukri publisher is paused, and Workday returned repeated 429s. Instahyre is disabled in the compared environments. |
| 25 remaining parity targets | Avature, BambooHR, Breezy HR, Cutshort, Eightfold AI, Freshteam, Hireology, Hirist, HRsmart, iCIMS, Jibe (iCIMS), Jobvite, Oracle Cloud Recruiting, Paycom, PeopleStrong, Phenom People, Recruitee, Rippling ATS, SAP SuccessFactors, Oracle Taleo, Teamtailor, UKG Pro / UltiPro, Wellfound, Y Combinator, Zoho Recruit. Some have board detection and still need a fetching path and live acceptance. |
| Additional requested coverage | Indeed and Flexiple. Indeed can start with authorized saved-search email intake while partner-feed access is evaluated. Flexiple's own company openings, its syndicated listings, and client opportunities are distinct. For client opportunities, evaluate a permitted integration or user-authorized intake. |

In the production check around 15:00 IST, SmartRecruiters completed 281 of 281 runs and added 54 records over 24 hours. LinkedIn completed 16 of 22 runs, added 90 records, and recorded six HTTP 429 responses. Naukri completed zero of 287 runs, and its relay had no recent snapshot. Preserve the owner's publisher pause until authorized to resume it. Workday recorded 24 rate-limit responses across 24 production runs. Marketplace email timings must be reported separately from direct-board discovery timings.

Promote the additional boards for the six healthy production providers and the new Lever provider in a bounded production batch. Before approval, observe 24 hours of recurring development runs, check baseline suppression and idempotency across the proposed boards, and verify one fresh matching posting reaches a private pilot Telegram chat. Record the image revision, backup, source flags, and rollback command. Run the same gate separately for recovering and new providers. The earliest candidate window is the afternoon of 24 November IST, conditional on the evidence, Telegram pilot readiness, and release approval.

The production bot has a linked private chat, with per-user opt-in currently off. The ledger has historical per-user LinkedIn sends, plus older legacy LinkedIn and Naukri sends. Production SmartRecruiters already fetches jobs, so an opted-in private account can test a new matching posting without waiting for the expanded-board release. The default development container has no bot, links, or opt-ins. Use a separate bot and explicitly linked private recipient for testing the expanded board set in development. Verify receipt, the source label and apply link, replay the poll, and check that it generates no duplicate alert or first-snapshot backfill.

## After discovery is proven

| Milestone | User experience |
| --- | --- |
| Telegram delivery | Send a fresh match from the normal pipeline to a linked, opted-in private chat. Repeat the poll and verify one canonical job and one alert. Measure discovery-to-acceptance separately from actual receipt. |
| Account and résumé onboarding | Create an account, upload a résumé, and review suggested roles, skills, experience, and locations before saving. Connect Telegram from the same flow and choose delivery preferences. Allow users to edit and delete their résumé and profile. |
| Application workspace | Save a job, tailor a résumé and cover note against the original description, review changes, and track the application and next action. Use the uploaded résumé as the source of factual claims. |
| Referral research and follow-up | For a job the user selects, find relevant people using permitted sources, explain each contact's relevance, and draft a referral request or follow-up. Track replies and stop scheduled follow-ups on reply or opt-out. Send only through authorized integrations and with explicit user control over the recipient, channel, and message. Use a manual handoff where LinkedIn invitations or messaging lack approved integration access. |

Keep the existing Python application and separate provider, extraction, and delivery responsibilities in code. Add a dedicated collector process if measurements show that collection interrupts web requests or alerts. Consider a different runtime only for a measured processing bottleneck.
