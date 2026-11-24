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

| Status as of 24 November 2026 | Providers |
| --- | --- |
| 30 development providers with successful scheduled ingestion | Ashby, Avature, BambooHR, Breezy HR, Cutshort, Darwinbox, Eightfold AI, Freshteam, Greenhouse, Hireology, HRsmart, iCIMS, Instahyre, Jibe (iCIMS), Jobvite, Keka, Lever, Oracle Cloud Recruiting, Oracle Taleo, PeopleStrong, Phenom People, Recruitee, Rippling ATS, SAP SuccessFactors, SmartRecruiters, Teamtailor, UKG Pro / UltiPro, Workable, Y Combinator, Zoho Recruit. Six of the original cohort also had successful recent production polls. New cohorts have their own release observation windows. |
| Three existing adapters that need separate acceptance | LinkedIn, Naukri, Workday. LinkedIn is intermittently live in production. The Naukri publisher is paused, and Workday returned repeated 429s. |
| Three remaining parity targets | Hirist, Paycom, Wellfound. |
| Additional requested coverage | Indeed and Flexiple. Indeed can start with authorized saved-search email intake while partner-feed access is evaluated. Flexiple's own company openings, its syndicated listings, and client opportunities are distinct. For client opportunities, evaluate a permitted integration or user-authorized intake. |

In the production check around 15:00 IST, SmartRecruiters completed 281 of 281 runs and added 54 records over 24 hours. LinkedIn completed 16 of 22 runs, added 90 records, and recorded six HTTP 429 responses. Naukri completed zero of 287 runs, and its relay had no recent snapshot. Preserve the owner's publisher pause until authorized to resume it. Workday recorded 24 rate-limit responses across 24 production runs. Marketplace email timings must be reported separately from direct-board discovery timings.

Promote the additional boards for the six healthy production providers and the new Lever provider in a bounded production batch. Before approval, observe 24 hours of recurring development runs, check baseline suppression and idempotency across the proposed boards, and verify one fresh matching posting reaches a private pilot Telegram chat. Record the image revision, backup, source flags, and rollback command. Run the same gate separately for recovering and new providers. The earliest candidate window is the afternoon of 24 November IST, conditional on the evidence, Telegram pilot readiness, and release approval.

The production bot has a linked private chat, with per-user opt-in currently off. The ledger has historical per-user LinkedIn sends, plus older legacy LinkedIn and Naukri sends. Production SmartRecruiters already fetches jobs, so an opted-in private account can test a new matching posting without waiting for the expanded-board release. The default development container has no bot, links, or opt-ins. Use a separate bot and explicitly linked private recipient for testing the expanded board set in development. Verify receipt, the source label and apply link, replay the poll, and check that it generates no duplicate alert or first-snapshot backfill.

The owner entered the pilot token through a hidden SSH prompt. Telegram verified `@YourJobBeeperDevBot` as distinct from production. Development Compose loads it from the mode-0600 file `/home/ubuntu/.config/job-beeper/dev-telegram.env`. The legacy broadcast chat ID is blank. The pilot uses a temporary VM service, `jobbeeper-telegram-pilot.service`, to receive Telegram updates and pass private link commands to the authenticated loopback webhook. This requires no public development ingress. The service restarted on 24 November with a 24-hour lifetime. The account owner generates the link in **Preferences**, opens it in Telegram, presses **Start**, refreshes the connection status, and enables matching new-job alerts. [Telegram Bot API](https://core.telegram.org/bots/api#getting-updates)

### Source Health administration

Source Health opens with enabled sources, plain-language status, jobs added in the past 24 hours, and last check time in IST. Paused sources and optional tools are collapsed. Use **Configure sources** to open the provider toggles in Preferences, then **Save Preferences**. Use **Employer boards** to find, verify, and activate a public career board. Directory and manifest imports are under **Candidate imports**. **Technical diagnostics** contains board schedules, host limits, and raw run errors. These tools load when opened, and **Refresh status** also refreshes the open tools.

### Recruitee pilot

Recruitee uses its [documented public formatted XML feed](https://support.recruitee.com/en/articles/8213076-faq-api). The development pilot uses the public Tether board at a five-minute interval. The production default is off. The collector streams a bounded response, uses feed publication timestamps, keeps multiple locations and explicit workplace flags, and uses a stable per-board offer ID. It participates in verification, activation, host cooldowns, and first-snapshot alert suppression.

On 23 November, development revision `5d3dab3` passed 303 provider, scheduler, and dashboard tests on Linux. The first scheduled poll at 16:09 IST saved 206 unique Tether listings and marked each as initial inventory for alert suppression. The development schedule now has 23 boards across eight providers. The feed supplied a description, a minute-precision publication time, and a direct Tether link for every listing. Twenty-one included India in their locations. The saved jobs include 53 description-derived experience values and 57 lower-confidence inferred values. For example, the Delhi Automation QA Engineer listing included “4+ years in QA automation” and TypeScript, and the normalized minimum was four years. The initial snapshot cannot establish fresh discovery or delivery latency.

The next scheduled poll at 16:15 IST again saw 206 postings and inserted zero duplicates. Both polls succeeded without HTTP 429 responses.

Development revision `d9a2519` applies Jobs Feed filters before pagination. Keep **Last 72 hours** to browse recent postings or select **Any posting date** to include older postings discovered in the current feed window. The 43 focused Linux tests passed. In the browser, Source Health showed Recruitee as healthy. Searching Recruitee for India showed zero postings under **Last 72 hours** and 21 under **Any posting date**. The Delhi QA listing displayed its description, four-year minimum, location, and direct application link.

### Expanded public board rollout · 23 November 2026

The following groups ran through the same persistent scheduler and left their first inventory marked for alert suppression. First-poll counts are unique source listings. They can include jobs published before the rollout.

| Development revision | Scheduled boards and first-poll counts | Verification |
| --- | --- | --- |
| `64481a4` | Teamtailor and DrDoctor on Teamtailor (16 and 2), Themis Insight on Breezy HR (38), Fly.io on BambooHR (9), AArete on Jobvite (23), and Smart Start on Hireology (2) | 333 Linux tests. All six boards already repeated successfully with zero new rows and zero 429s. Breezy HR and Jobvite each filled 10 more descriptions on the repeat. |
| `6e884dc` | Bloomberg on Avature (72), Amyx on iCIMS (96), Black Box on Oracle Cloud Recruiting (390), RealWork on Rippling ATS (4), and Y Combinator’s India listing page (28) | 77 Linux tests. All first polls succeeded without rate limiting. |
| `1f2edad` | Getinz on Freshteam (50) and Cutshort’s software engineering listing (38) | 43 Linux tests. Both first polls succeeded. All 38 Cutshort jobs had descriptions and employer-stated experience bounds. |
| `d6e0e22` and `adcc9fc` | BC Public Service on HRsmart (25), TVO on UKG Pro (3), and Philips on Phenom People (56) | 112 Linux tests after normalizing timestamp offsets for Python compatibility. The three sources first ran together on `aece006`. |
| `aece006` | Instahyre’s Bangalore city search (140) | 43 focused Linux tests passed. The first development poll marked the initial city inventory for alert suppression. Instahyre runs as a scheduled city search. |

The new public board path reuses configuration validation, host limits, persistent schedules, baseline suppression, and source-health reporting. The verification and collector use the same public listing source. Employer jobs can be added through **Source Health → Employer boards**. Search for candidates first, verify the public endpoint, then activate the board. Employer site scanning and applicable Common Crawl domains can discover and stage additional boards.

Teamtailor serves a [public RSS feed](https://support.teamtailor.com/en/articles/11171756-rss-feed-how-to-guide). Oracle Cloud’s [public requisition list](https://docs.oracle.com/en/cloud/saas/human-resources/farws/api-recruiting-ce-job-requisitions.html) and [requisition details](https://docs.oracle.com/en/cloud/saas/human-resources/farws/Recruiting__Recruiting_CE_Job_Requisition_Details.html) provide distinct list and detail fields. Where a list omits its full description, the collector fetches up to ten details per board per poll. It prioritizes newly observed jobs and revisits pending ones. The title and reference appear immediately, and Telegram eligibility waits for a description. A field remains unknown until its source supplies a usable value. Date-only postings and jobs lacking a publication timestamp cannot supply minute-level discovery-lag measurements.

The development providers in these groups default to off in production. Each cohort needs repeated live polling, description verification, a genuinely fresh posting for latency measurement, and the Telegram receipt check before promotion.

The browser showed 24 enabled sources and zero needing attention. In **Jobs Feed**, choosing **Cutshort**, **Any posting date**, and searching for **Jaipur** displayed two listings. The KDK Software listing showed Jaipur, an employer-stated range of four to six years, TypeScript among the source skills, its description, and a direct link to the same posting.

At approximately 17:52 IST, the development scheduler had 39 active employer boards, each with a successful latest poll. Instahyre was also healthy on its ten-minute city search. The 16 sources added in these groups had stored 993 distinct source listings, including 992 first-snapshot rows. There were 396 full descriptions at this checkpoint, with remaining details scheduled under the per-poll cap where available. The 44 recorded runs were successful, including 26 runs that added zero rows, with no HTTP 429s. The only listing observed after its baseline had been published more than ten days earlier, so these runs did not provide a fresh discovery-latency sample. The earlier release cohort had accumulated about three hours of its 24-hour observation window. The expanded development bot was still unconfigured.

### Fresh posting measurements · 23 November 2026

At approximately 19:51 IST, development had measured 46 non-baseline listings whose sources reported a minute-precision publication time within the current observation window. This includes MongoDB’s Software Engineer 3 on Greenhouse, observed 103 seconds after its reported publication time. The p95 below uses the nearest rank within each provider’s sample.

| Provider | Timed listings | Within 180 seconds | p95 |
| --- | ---: | ---: | ---: |
| Ashby | 2 | 1 | 350 s |
| Greenhouse | 8 | 7 | 201 s |
| Recruitee | 1 | 0 | 241 s |
| SmartRecruiters | 35 | 4 | 1,071 s |

These timings cover discovery. Telegram delivery still needs a receipt from the private pilot. The original observation window had run for 5.12 hours at this checkpoint. The checked Adobe and Mastercard public Workday boards both returned HTTP 429 from the VM, so Workday still needs a healthy public or approved feed before another rollout.

At 21:39 IST, the sample had grown to 56 eligible postings. Discovery took at most three minutes for eight of 11 Greenhouse postings, one of three Ashby postings, and four of 41 SmartRecruiters postings. The single Recruitee sample took 241 seconds. The expanded p95 was 1,061 seconds for Greenhouse, 583 seconds for Ashby, and 1,071 seconds for SmartRecruiters. The broader sample supports provider-specific latency reporting and further tuning before offering a delivery-time guarantee.

During the same observation window, Lever’s Palantir board intermittently timed out on listing pages. The scheduler retained the successful first page when page two timed out and applied board-level backoff. The production batch can include only boards with healthy recurring polls and idempotent replay.

### Zoho Recruit and Oracle Taleo · 23 November 2026

Zoho Recruit revision `47adc9f` passed 100 Linux tests. Its public career pages use a case-preserving page name to select the published list and per-job details. Exoscale returned seven openings. MADIFF Polska returned 38 on its scheduled retry after the first list request timed out. All 45 jobs were marked as initial inventory for alert suppression. Both boards repeated successfully with zero duplicates. By 21:07 IST the scheduler had recorded 15 successful Zoho runs, and all 45 jobs had descriptions. The adapter stores Zoho’s opening date as source metadata where present and leaves the publication timestamp unknown, so the field does not enter discovery-lag calculations.

Oracle Taleo revision `cf476ee` uses the classic public search layout. Chicago’s first scheduled poll returned ten distinct requisitions with day-precision posting dates and marked them as initial inventory. The collector uses the employer’s anonymous page and form for each read. It retains the posting ID, publication day, description, qualifications, and available location. The pilot polls the newest results page. Oracle separately offers per-career-section RSS when enabled by the employer. [Oracle Taleo RSS configuration](https://docs.oracle.com/en/cloud/saas/taleo-enterprise/20d/otcug/social-media.html)

Chicago’s scheduled repeat at 21:17 IST returned the same ten jobs and added zero duplicates. Seven had full descriptions. Three public detail requests still failed on the repeat, including a reproduced HTTP 500 from the provider. Jobs awaiting a description remain in the feed but do not qualify for alerts.

The Linux suites passed 123 tests for Taleo, 143 after revision `2f4ab5d` added support for parenthesized experience requirements, and 37 Telegram tests using a simulated sender. In the deployed browser, both provider rows were healthy. The Taleo Director of Public Affairs listing showed Chicago, its direct application link, and the nine-year minimum from the description. The Zoho filter showed Exoscale’s Site Reliability Engineer listing with its description and direct application link.

For another employer, use the complete Zoho public career-page URL or the Oracle Taleo public career-section search URL in **Employer boards**. Verify the endpoint before activation. The Taleo probe expects the classic page layout used by Chicago; a different layout needs its own verification.

### SAP SuccessFactors and PeopleStrong · 23 November 2026

SAP SuccessFactors revision `c9920fa` reads the newest public search results from the verified Boston Scientific and Lubrizol career sites. Each test request returned 25 distinct openings. Canonical links retain the employer domain and requisition ID, including URLs with non-English titles. The adapter reads the public job description and stores provider dates at day precision. More custom career domains can be added after verifying their search layout. [SAP career-site search settings](https://help.sap.com/docs/successfactors-recruiting/setting-up-and-maintaining-sap-successfactors-recruiting/career-site-admin-search-settings)

PeopleStrong revision `03b36dc` uses the Muthoot Pappachan Group candidate portal. Its public feed returned 45 jobs from the first page. It takes only the fields shown to applicants and requests the public description separately. A Muthoot Fincorp Business Development Officer posting supplied Chikiti, a zero-to-four-year range, business development skills, and a full description. Use the `/job/joblist` URL for another compatible PeopleStrong board and run **Verify** in **Employer boards**. [Muthoot candidate portal](https://mpgcareers.peoplestrong.com/job/joblist)

Revision `c596d1a` adds explicit provider skills to preference matching. Job descriptions and provider skill labels both contribute to the skill score, and a skill found in both contributes once. The matcher continues to distinguish an employer-stated experience range from a range inferred from a job description.

### Eightfold AI · 23 November 2026

Revision `b126d1e` uses the candidate site’s public **Latest** search with the verified tenant for Eightfold’s own openings. The live adapter test returned all 43 current public results in five pages. It retains direct job links, multiple locations where the source provides them, workplace type, posting timestamp, and public descriptions. It polls every 15 minutes in development and keeps the employer-specific host and tenant fixed. Other employer career sites require verification before adding them. Eightfold also offers employer-enabled XML distribution and daily public sitemaps. [Eightfold public careers](https://app.eightfold.ai/careers/search) · [Eightfold job feed documentation](https://docs.eightfold.ai/source-tracking/pcs-source-implementation-checklist-and-configuration)

By 21:35 IST, the seven new boards across Zoho, Taleo, SuccessFactors, PeopleStrong and Eightfold had saved 193 public listings as initial inventory. Development had 46 active employer schedules across 28 ATS and marketplace sources, plus Instahyre’s city search. The two SAP sites supplied 25 listings each, PeopleStrong supplied 45, and Eightfold supplied 43. The first snapshots seeded the feed and were suppressed for Telegram.

The deployed browser showed these five providers in **Source Health** and returned jobs from each provider in **Jobs Feed**. PeopleStrong’s Chikiti posting showed its employer-stated 0–4 years, key skills, description, and direct link. Lubrizol’s Senior Process Engineer posting showed Corona and a description-derived 5+ years. Eightfold’s Product Manager II posting showed Bengaluru, hybrid work, its description and direct link, and a separately labeled low-confidence experience inference.

The scheduled repeats on both Zoho boards, PeopleStrong, Boston Scientific, Eightfold, and the first Taleo repeat added zero duplicates. On later runs, Lubrizol added Manufacturing Regional Process Technologist and Chicago added Program Manager as new-to-feed requisitions beyond initial inventory. Both carried day-precision dates, so these observations are excluded from minute-precision latency measurements.

All 655 Linux tests passed on `b126d1e`. After the full suite, the browser showed 29 enabled sources with zero needing attention and reopened the Bengaluru Eightfold job with its direct link. Palantir's Lever board also completed its next scheduled retry. Its earlier timeouts remain relevant to the production observation window.

### Jibe India pilot and source recovery · 23 November 2026

The PepsiCo Jibe board uses the provider's public India country filter. Its first scheduled poll at 22:16 IST saved 206 distinct jobs with descriptions and marked all 206 as initial inventory for alert suppression. The matcher extracted a numeric experience requirement for 174 jobs. Public descriptions, separate qualifications and responsibilities, posting timestamps, and locations are retained. The adapter polls up to three pages of 100 results for this filter and links to the employer's public detail page. The broader Costco board also returned real jobs in a public probe. [PepsiCo careers](https://www.pepsicojobs.com/main/jobs?country=India) · [Costco careers](https://careers.costco.com/jobs)

The local Naukri relay mode consumes `/data/naukri-relay.json` when `JOB_BEEPER_NAUKRI_RELAY_MODE=local`. It applies the same age, future timestamp, count, and snapshot fingerprint checks. A VM publisher can write the existing JSON contract to a temporary file and rename it atomically. The owner reported the GitHub Actions budget is exhausted, so a fresh authorized Naukri snapshot producer is still needed. Official job-alert emails are one intake option. [Naukri job alerts](https://resume.naukri.com/frequently-asked-questions-faq/how-to-create-free-job-alerts/)

Cisco and Accenture Workday list probes returned 200 and 20 jobs each on the VM. Cisco's follow-up received HTTP 429. Workday remains paused in development. The revised collector caches successful job descriptions for 24 hours, spaces detail requests, and deduplicates the same public URL across inventory and freshness pages. LinkedIn now reuses verified descriptions for 24 hours, with expiration and re-fetch covered by its regression test. The observed production LinkedIn window had two runs in three hours and added 24 listings, including a partial rate-limited run. Acceptance requires recurring healthy polls at the configured pace.

The development admin can link Telegram through the exact pilot ID configured in the private environment. The pilot gate preserves existing member controls and limits admin access to the designated account or the existing Gmail owner path.

### Instahyre details and overnight polling · 24 November 2026

The Instahyre search API supplied the Increff listing's four skill tags, title and Bangalore location. Its advertised record endpoint returned the same fields. Both omitted the full job description and experience. The original page shows 3–5 years in its header and a 2–5-year requirement in the description. The matcher uses the explicit description range. The inspector displays the source header range separately alongside Java, React, React.js and Spring Boot, and renders the requirements as a list. The inspector now labels metadata with the actual provider and uses the authorized detail endpoint when opening a job outside the current feed page. [Increff listing](https://www.instahyre.com/job-446772-sde-ii-full-stack-at-increff-bangalore/)

The development VM received HTTP 403 on the public Instahyre detail page. The collector still ingests the search feed, saves its skill tags as structured data, checks robots policy before detail requests, and backs off those requests for at least six hours on access restrictions or rate limits. The existing Increff development row `5925` was updated using the description verified in the browser. The update preserved the original job and canonical IDs plus discovery and posting timestamps. Search-only polls retain verified details. Other restricted descriptions remain unavailable until Instahyre serves them through an accessible source.

By 08:41 IST, the Jibe pilot recorded 42 successful runs, 211 distinct PepsiCo listings with descriptions, and zero HTTP 429 responses. The first 206 rows were initial inventory. Five later postings had minute-precision source timestamps and were discovered 6–16 minutes after publication on the 15-minute schedule. The development Telegram pilot had zero linked private chats and no delivery to measure at this checkpoint.

The PepsiCo public search defaults to relevance. Its **Posted** sort requests `sortBy=posted_date`, which returned the first 100 timestamps in descending order in the VM probe. Revision `6ecd31d` applies this sort before paging. The first three five-minute development runs from 09:11 IST succeeded with 211 jobs per run, zero inserts and zero rate-limit responses. Assess latency using the next new postings with minute-precision publication evidence. [PepsiCo careers](https://www.pepsicojobs.com/main/jobs?country=India)

All 662 V2 tests passed on the VM at `6ecd31d`. The signed-in integrated browser opened the repaired Increff detail by direct dashboard link, showed nine real list items, and displayed the four source skill tags and both experience ranges. It also opened PepsiCo’s Associate Digital Designer detail with Hyderabad, a 6–7-year requirement and the employer apply link. The PepsiCo sample repeats responsibilities and qualifications supplied both in its overview and as separate source fields. Deduplicate overlapping sections when extending formatted descriptions to Jibe.

### Provider data still needed

| Providers | Evidence and integration path |
| --- | --- |
| Hirist and Wellfound | The public Hirist job index returned HTTP 403 from the VM. Wellfound’s public India software listings returned a challenge. Wellfound documents daily or weekly saved-search email alerts. A provider feed or authorized mailbox sample is still needed. [Hirist index](https://www.hirist.tech/k/-jobs) · [Wellfound saved searches](https://help.wellfound.com/article/782-saved-searches) |
| Paycom | Public job details return JobPosting data. The checked ARC, Lasell and Taylor Metal career portals exposed no usable listing response. Taylor Metal's rendered browser shell loaded its app manifest. The sitemap path identified in Paycom’s robots file returned HTTP 404 on the VM. The bounded Common Crawl index probe returned HTTP 504. A working employer index or approved feed is needed for recurring discovery. The owner has no jobs-feed key for this pilot. [Taylor Metal careers](https://taylormetal.com/jobs) · [Paycom public job example](https://www.paycomonline.net/v4/ats/web.php/portal/D52435485532E6BB0432223C90E2B6D7/jobs/439148) |
| Indeed | Evaluate an approved publisher or partner integration. User-authorized saved-search alerts are a separate intake option. [Indeed publisher documentation](https://docs.indeed.com/indeed-plus/publisher-js-plugin) |
| Flexiple | The checked public jobs path redirects to the talent page, which describes matching for members. Validate an approved talent opportunity feed or user-authorized alerts. [Flexiple talent page](https://flexiple.com/talent) |
| HiringCafe | Its official MCP connector supports on-demand conversational search and returns employer apply links. The documented ChatGPT connector excludes heavy automation, and the terms restrict redistribution. Ask for an approved feed before using HiringCafe for unattended JobBeeper ingestion. [HiringCafe connector](https://hiringcafe.com/documentation/hiringcafe-chatgpt-app) · [HiringCafe terms](https://hiringcafe.com/terms-and-conditions) |

## After discovery is proven

| Milestone | User experience |
| --- | --- |
| Telegram delivery | Send a fresh match from the normal pipeline to a linked, opted-in private chat. Repeat the poll and verify one canonical job and one alert. Measure discovery-to-acceptance separately from actual receipt. |
| Account and résumé onboarding | Create an account, upload a résumé, and review suggested roles, skills, experience, and locations before saving. Connect Telegram from the same flow and choose delivery preferences. Allow users to edit and delete their résumé and profile. |
| Application workspace | Save a job, tailor a résumé and cover note against the original description, review changes, and track the application and next action. Use the uploaded résumé as the source of factual claims. |
| Referral research and follow-up | For a job the user selects, find relevant people using permitted sources, explain each contact's relevance, and draft a referral request or follow-up. Track replies and stop scheduled follow-ups on reply or opt-out. Send only through authorized integrations and with explicit user control over the recipient, channel, and message. Use a manual handoff where LinkedIn invitations or messaging lack approved integration access. |

Keep the existing Python application and separate provider, extraction, and delivery responsibilities in code. Add a dedicated collector process if measurements show that collection interrupts web requests or alerts. Consider a different runtime only for a measured processing bottleneck.

### Empty-preference browsing · 24 November 2026

New members can open the shared jobs feed before completing matching preferences. The dashboard still applies its freshness, source, search, score, remote-only, alertable and sort controls, with the default view covering the last 72 hours. Selecting `Any posting date` removes the age cutoff. Personalized matching and alert eligibility begin after the member saves a target role plus a location or Remote only.

The mobile navigation keeps `Preferences` and `Account` as separate destinations so configuration and account access remain discoverable on narrow screens.

Opportunity rows use a wrapped, width-constrained source and action area at split-pane widths. The `aggregated` marker means the job belongs to a canonical opportunity that may represent equivalent records from multiple providers. It does not mean the job was fetched from every provider shown in the row.
