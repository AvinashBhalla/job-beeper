# JobBeeper product plan

JobBeeper should help a user discover relevant openings, decide which ones to pursue, and track each application through follow-up. The first release milestone is a shared, continuously maintained job feed and measured delivery of new matches.

## Milestone 1 · Discovery and alerts

1. Validate the existing Greenhouse collector on a small set of boards relevant to India and remote roles. Suppress alerts for the first successful snapshot and persist new jobs from later polls. Compare title, employer, location and remote eligibility, skills, experience requirements and direct application link with the original posting. Preserve whether a field came from the employer or was inferred from the description.
2. Record discovery lag using source publication timestamps with time-of-day precision. Measure discovery-to-queue and discovery-to-Telegram acceptance from persisted records. Report the sample sizes and missing timestamps alongside percentiles. API acceptance and seeing a message in the recipient's private chat are separate checks.
3. Pass a live alert through the normal pipeline to an opted-in private pilot chat. Repeat the poll and verify that the job remains one canonical opportunity and the user receives one alert. Check the normal Dashboard and Source Health screens. A collection run with no new postings or a run with zero eligible alerts does not establish real-time delivery.
4. Repeat the same acceptance criteria with Lever or Ashby. Grow coverage through a shared verified board catalog, then add Workday and Darwinbox where individual employer boards can be verified. Use employer career links, sitemaps, and public or licensed directories for discovery seeds. Add legitimate platform alert emails or authorized aggregator feeds as supplementary inputs with separately measured latency and unique yield.
5. Keep provider collectors behind a common input contract. Reuse the scheduler, normalized job records, matcher, and delivery ledger. Give frequently changing boards shorter intervals within host budgets. Keep ambiguous employer associations in review. Use board freshness, active coverage, unique relevant job yield, rate-limit responses, and delivery latency to prioritize the next connector.

For priority boards with reliable timestamps, the initial objectives are p95 publication-to-discovery at or below 180 seconds and p95 discovery-to-Telegram acceptance at or below 30 seconds for eligible alerts during delivery hours. These objectives need representative samples. Backfill, source timestamps with date-only precision, and retries after ambiguous delivery outcomes need separate interpretation.

### Development pilot

The isolated dev Compose configuration uses two-minute Greenhouse polls over Coinbase, Graviton Research Capital, and Zocdoc. Existing database state and initial-baseline suppression are retained. The default dev instance keeps Telegram credentials blank. A live delivery test needs an isolated bot and a private account connected and opted in through JobBeeper.

Read the pilot window from the application's data volume using the deployment start time as the cutoff. The tool reads the existing database without changing it or delivering alerts.

```sh
docker exec job-radar-dev python -m v2.discovery_pilot --db /data/jobs.db --source greenhouse --since 2026-11-23T07:44:42Z
```

On 23 November 2026, development commit `5f62427` passed 48 focused tests on both Windows and the Linux VM, plus four baseline and database tests on Linux. Two live cycles each returned 252 Coinbase jobs, 20 Graviton Research Capital jobs, and 66 Zocdoc jobs. All six polls succeeded with zero new rows and zero HTTP 429s. The browser showed the existing feed, description-derived experience, direct links, and all three boards scheduled at 120 seconds. These cycles yielded zero publication-lag and Telegram delivery samples.

When a configured interval decreases, the scheduler now advances a healthy board's next due time from its last successful poll. The host request spacing, active leases, and failure cooldowns still apply. Verify the next checkpoint with a newly observed posting before assessing latency targets or promoting the pilot into a wider rollout.

## After discovery is proven

| Milestone | User experience |
| --- | --- |
| Account and résumé onboarding | Create an account, upload a résumé, and review suggested roles, skills, experience, and locations before saving. Connect Telegram from the same flow and choose delivery preferences. Allow users to edit and delete their résumé and profile. |
| Application workspace | Save a job, tailor a résumé and cover note against the original description, review changes, and track the application and next action. Use the uploaded résumé as the source of factual claims. |
| Referral research and follow-up | For a job the user selects, find relevant people using permitted sources, explain each contact's relevance, and draft a referral request or follow-up. Track replies and stop scheduled follow-ups on reply or opt-out. Send only through authorized integrations and with explicit user control over the recipient, channel, and message. Use a manual handoff where LinkedIn invitations or messaging lack approved integration access. |

Keep the existing Python application and separate provider, extraction, and delivery responsibilities in code. Add a dedicated collector process if measurements show that collection interrupts web requests or alerts. Consider a different runtime only for a measured processing bottleneck.
