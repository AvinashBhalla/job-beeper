# Job Radar V2 — Agent Handover & Product Source of Truth

> **Purpose:** This document is the durable handover for Job Radar V2.
> A future agent should read this file before making architectural or product changes.
> Do not depend on chat history being available.

**Last verified:** 2026-10-08 (Oracle runtime verification + canonical dedupe implementation)  
**Active branch:** `v2-live-radar`  
**Repository:** `AvinashBhalla/job-beeper`

> **Reconciliation note:** This document was updated after a direct repository review. Where older handover claims conflicted with current code, the current code/runtime state is recorded below. In particular: V2 Telegram is not yet implemented; cross-source canonical dedupe is incomplete; the current Naukri relay schema does not guarantee structured experience/skills fields; and the repository must not claim a reproducible systemd scheduler unless its unit files are committed.

---

## 1. PRODUCT GOAL

Job Radar is a **personal, always-on job discovery and matching system**.

The objective is not to build a generic scraper or a dashboard full of jobs.

The intended experience is:

```
Continuously discover fresh jobs
        ↓
Normalize and store them
        ↓
Deduplicate the same opportunity across sources
        ↓
Apply the user's configurable job preferences
        ↓
Reject irrelevant / unsuitable jobs
        ↓
Rank genuinely relevant jobs
        ↓
Explain why each job matched
        ↓
Send only worthwhile new matches to Telegram
        ↓
Provide a simple live frontend for review and configuration
```

### Product priorities

1. **Freshness**
2. **Correctness of matching**
3. **Low-noise Telegram alerts**
4. **Persistence / reliability**
5. **Cross-source deduplication**
6. **Simple useful frontend**

The UI is secondary to the backend job radar.

The system must never invent a posting timestamp just to make a job appear fresh.

---

## 2. CANDIDATE PROFILE / DEFAULT TARGET

Current candidate experience:

- 2 years

Current maximum acceptable experience:

- 3 years

Current target locations:

- Bengaluru / Bangalore
- Gurugram / Gurgaon
- Delhi
- Remote India

Current target role families include:

- Software Engineer / Software Developer
- Full Stack Engineer / Developer
- Frontend Engineer / Developer
- Backend Engineer / Developer
- React / React Native
- Python
- Node / Next
- Automation Engineering
- AI / ML
- LLM
- Forward-Deployed Engineering

Current skill vocabulary includes:

- React
- React Native
- Next.js
- Node.js
- Python
- FastAPI
- Django
- JavaScript / TypeScript
- Automation
- n8n
- API
- LLM
- AI
- OpenAI
- Gemini
- Workflow
- Orchestration

These are **defaults, not permanent hardcoded product rules**.

User preferences must ultimately be configurable from the frontend.

---

## 3. DESIRED ARCHITECTURE

```
                 ┌──────── LinkedIn
                 │
                 ├──────── Naukri
                 │            ↑
                 │       GitHub relay
                 │
                 ├──────── Instahyre
                 │
                 └──────── ATS / career sources
                              │
                              ▼
                       Source adapters
                              │
                              ▼
                         Normalize
                              │
                              ▼
                   Canonical job identity
                              │
                              ▼
                     Cross-source dedupe
                              │
                              ▼
                       Persistent SQLite
                              │
                              ▼
                     New / changed detection
                              │
                              ▼
                    Deterministic matching
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                 Telegram           Frontend
```

### Infrastructure

Primary persistent runtime:

- Oracle Cloud Always Free VM
- Ubuntu
- Docker
- SQLite on a persistent Docker volume

GitHub Actions is **not** the persistent scheduler/runtime.

GitHub Actions is currently used as the Naukri acquisition environment because direct Naukri access from Oracle was unreliable.

---

## 4. WHY V1 WAS ABANDONED

V1 relied heavily on:

- GitHub Actions as a scheduler
- JSON state
- broad web discovery
- manually curated ATS/company lists
- fragile Naukri/browser scraping
- weak matching
- stale frontend data

Problems included:

- scheduled workflows were unreliable
- LinkedIn freshness was inconsistent
- Naukri was fragile
- matching was weak
- frontend data became stale
- manual scan behavior defeated the idea of a continuous radar

V1 remains useful as reference/fallback only.

Do not recreate the V1 architecture unless there is a specific, justified reason.

---

## 5. IMPORTANT SOURCE DECISIONS

### LinkedIn

Current approach:

- public logged-out guest jobs endpoint
- low-volume polling
- newest-first
- six-hour safety window
- deduplicate using stable LinkedIn job IDs
- record source posting time separately from discovery time
- retry/backoff on 429 and transient 5xx errors

Current V2 poll target:

- 120 seconds

LinkedIn direct collection from Oracle has been **proven**.

### Naukri

Direct Naukri access from Oracle was abandoned after:

- JobSpy Naukri API returned 406
- Playwright / Chromium hung
- Python requests hung
- curl timed out

Do **not** restart Oracle-side Chromium/Naukri scraping.

Current architecture:

```
Oracle systemd timer
        ↓
gh workflow run naukri-relay.yml
        ↓
GitHub Actions runner
        ↓
Naukri
        ↓
naukri-relay branch
        ↓
naukri_relay.json
        ↓
Oracle V2
```

The corrected relay was successfully proven on 2026-10-08.

Example successful relay properties:

- workflow run succeeded
- `naukri_relay.json` was published
- count = 150 jobs
- real Naukri JSON was accessible from the relay branch

### Instahyre

Currently experimental and **disabled by default in V2**.

The current public JSON probe returned HTTP 400 for the tested request. We do not treat this as a reliable source until its current interface is verified.

Repository defaults and the V2 runtime migration now make Instahyre opt-in. Config schema version 3 disables Instahyre when migrating a pre-v3 runtime config.

Zero results or request errors must not automatically justify increasing polling or scraping volume.

### Future ATS sources

The product should progressively prioritize structured/source-specific adapters such as:

- Greenhouse
- Lever
- Ashby
- SmartRecruiters
- Workday
- other useful ATS/career systems

Do not build one generic scraper for all sources.

---

## 6. NARROWING THE MATCHING PHILOSOPHY

Matching must be deterministic and explainable before any AI enrichment.

The target pipeline is:

```
source
 → normalize
 → canonical identity
 → deduplicate
 → new/changed detection
 → deterministic preference match
 → score + reasons
 → dashboard / Telegram
```

### Current matcher checks

- title exclusions
- location
- target role
- configured skills
- experience
- match score
- match reasons

### Current known matcher lessons

The first V2 matcher produced obvious false positives.

Example bad matches included:

- Accenture roles advertised as 3–8 or 3–15 years being accepted
- `ai` appearing as a false skill because of substring matching
- generic roles crossing the threshold only because they had a matching title

These were corrected.

Current matcher code was tightened in commit:

```
d5ec338 — V2: tighten experience and skill matching
```

The current matcher:

- uses phrase-aware matching rather than naive substring matching for configured terms
- rejects jobs whose stated minimum experience exceeds the candidate experience
- rejects jobs whose stated maximum range exceeds the configured 3-year ceiling
- retains match reasons
- can represent unknown experience

### Important policy principle

**Eligibility, score, and alertability are different concepts.**

A job can be:

- relevant enough to show in the frontend
- but not sufficiently verified to send to Telegram automatically

Unknown experience should therefore not automatically become a Telegram alert merely because title/location/skills look good.

The eventual product should expose an explicit configurable policy for this.

---

## 7. CURRENT CONFIGURATION PRINCIPLE

The current V2 implementation reads `v2/config.json`.

That is useful as a code-level default, but it is **not yet the final product behavior**.

### Required end state

The V2 runtime configuration layer is now implemented in the repository.

The frontend must allow the user to configure, without editing Python:

- target roles
- keywords
- skills
- locations
- remote preference
- candidate experience
- minimum job experience
- maximum acceptable experience
- excluded titles
- excluded role/category types
- maximum job age
- minimum match score / threshold
- whether explicit experience is required for alerts
- Telegram enabled/disabled
- source enable/disable where appropriate

User preferences should be persisted on the VM, not committed back into GitHub on every UI change.

Implemented direction:

```
Frontend
  ↓
V2 configuration API
  ↓
persistent /data/config.json
  ↓
matcher + alertability policy
```

Configuration updates are protected by a generated token stored at `/data/config_token` unless `JOB_RADAR_CONFIG_TOKEN` is supplied as an environment variable.

Application code and personal preferences remain separate.

The repository now exposes:
- `GET /api/config`
- `PUT /api/config` with `X-Config-Token`
- runtime config migration/default seeding
- validation for user-owned configuration
- live matching against runtime configuration without a rebuild

---

## 8. CURRENT FRONTEND STATUS

A dashboard already exists under:

- `dashboard/index.html`
- `dashboard/app.js`
- `dashboard/styles.css`

It includes:

- Jobs
- Applied
- Filters
- Settings
- Sources
- job detail view

The dashboard has now been rewritten to use the V2 local APIs for jobs, source status and configuration.

Current repository direction:

- configuration reads/writes through /api/config
- config token is held in browser session storage
- job feed reads from /api/jobs
- source health reads from /api/source-status
- V2 runtime serves the dashboard directly

Deployment/browser verification is still pending.

---

## 9. CURRENT INFRASTRUCTURE STATE — VERIFIED

### Oracle VM

VM:

- `job-radar`
- Oracle Always Free
- approximately 1 GB RAM
- 2 GB swap

The VM previously suffered from 208 zombie Chromium processes and very high CPU steal.

That issue was resolved.

Current V2 deliberately uses no Chromium.

### Docker

V2 container is running:

- service: `radar`
- container currently named similar to `v2-radar-1`
- port: `8000`
- database: `/data/jobs.db`

Health endpoint currently returns:

```json
{
  "status": "ok",
  "version": "2.0.0",
  "db": "/data/jobs.db"
}
```

### Naukri systemd scheduler

The following units exist:

- `job-radar-naukri-relay.service`
- `job-radar-naukri-relay.timer`

The timer is enabled and runs every five minutes.

The service executes:

```
/usr/bin/gh workflow run naukri-relay.yml --repo AvinashBhalla/job-beeper --ref main
```

GitHub CLI is authenticated for the `ubuntu` user.

The scheduler has successfully triggered the relay automatically.

### Do not manually trigger the relay during normal operation

With the five-minute systemd timer enabled, manual dispatches can create unnecessary overlapping relay runs.

Use manual dispatch only for debugging/recovery.

---

## 10. CURRENT LIVE INGESTION STATUS

The running V2 service has successfully demonstrated:

### Naukri

- 150 jobs obtained from relay during a run
- data persisted to SQLite
- source marked successful

### LinkedIn

- 177 jobs seen in the tested run
- 36 new jobs in that run
- source marked successful

### Instahyre

- 0 jobs
- currently experimental

The system is therefore **ingesting real jobs continuously**.

---

## 11. CURRENT RELEASE CHECKPOINT

### Completed

```
✅ Persistent Oracle VM
✅ Docker V2 runtime
✅ SQLite persistence
✅ LinkedIn direct ingestion
✅ Naukri GitHub relay
✅ Naukri corrected relay execution proven
✅ Oracle → GitHub workflow dispatch proven
✅ Oracle 5-minute Naukri scheduler
✅ V2 Naukri relay consumption
✅ Freshness/discovery timestamps separated
✅ Initial deterministic matcher
✅ Experience false-positive correction
✅ Phrase-aware skill/title matching
✅ V2 persistent runtime configuration API implemented
✅ Frontend connected to V2 configuration API in repository
✅ Config validation + generated configuration token
✅ Matcher regression tests added
✅ Experience-range parser fixed to preserve hyphen/en-dash ranges
✅ Runtime config migration hardened: pre-v3 configs now disable unverified Instahyre
✅ Thirteen matcher/dedupe/config regression tests are defined, covering experience parsing, alertability, config migration, canonical URL normalization, alias normalization, strong/ambiguous cross-source matching, and SQLite persistence
✅ Canonical opportunity schema and conservative cross-source linking implemented
✅ Canonical opportunity API added
✅ Canonical persistence/backfill regression tests added
✅ Conservative dedupe rule: auto-link only strong evidence; ambiguous metadata stays separate
✅ Cross-source dedupe diagnostic endpoint added for real LinkedIn/Naukri overlap validation
✅ Dedupe diagnostic optimized to group by normalized company/title identity before pair comparison
✅ Same-source canonical auto-linking disabled except exact canonical URL evidence
✅ Fixed canonical rebuild startup import regression after identity-version hardening
✅ Canonical identity version 2 triggers a clean rebuild of prior canonical assignments
✅ SQLite row-factory regression fixed in canonical assignment path
```

### Currently in progress

```
⏳ Validate the direct on-disk runtime config after API-triggered migration and test a real frontend config update
⏳ Deploy and validate canonical grouping against real LinkedIn + Naukri overlaps using `/api/dedupe-candidates` (company/title-bucketed path)
⏳ Confirm the v2 identity-version rebuild completes successfully on the persistent Oracle database
⏳ Validate rebuilt canonical groups and identify safe high-confidence cross-source merge signals
⏳ Separate observation/newness/eligibility/alert state before Telegram
```

### Not yet production-ready

```
❌ Telegram notification engine
❌ Cross-source canonical deduplication
❌ New/changed opportunity detection
❌ Fully V2-connected frontend settings
❌ Complete frontend live feed
❌ Source health UI beyond basic API
❌ V2 replacement of all useful V1 capabilities
```

### V1 status

The old V1 workflow still exists and may still send Telegram alerts.

Do not disable the V1 alert path until V2 Telegram is proven.

After V2 alerts are trustworthy:

- disable V1 duplicate notifications

---

## 12. IMMEDIATE NEXT STEPS

The next implementation sequence is:

### Step A — V2 persistent configuration

**Repository implementation is complete; Oracle verification is effectively passing.**

The runtime API now reports `config_version: 3` and `source_enabled.instahyre: false`. The first direct file read on Oracle still showed the legacy `config_version: 2` / Instahyre enabled state, but a subsequent `/api/config` read showed the v3 migrated state; this confirms the application-level migration path is active. A direct post-migration file read should still be performed once to remove ambiguity.

The latest code adds a config-schema v3 migration that explicitly turns Instahyre off for legacy/pre-v3 runtime configurations.

The runtime uses:

```
/data/config.json
```

and a protected V2 configuration API.

The API supports:

- read current settings
- update settings
- validate settings
- return current effective settings

The application should use the effective runtime configuration rather than immutable module-level values loaded only once at process startup.

### Step B — Configurable matching

**Partially implemented and regression-tested. The matcher/dedupe suite currently contains thirteen tests; Oracle deployment validation is pending for the new dedupe tests.**

The matcher now reads runtime configuration rather than fixed module-level preferences. Regression coverage exists for experience and phrase-aware skill/category matching.

Next: deploy and validate settings changes against the live database, then finish the distinction between `match`, `eligible`, and `alertable` for Telegram.

Do not hardcode:

- experience policy
- target roles
- location policy
- exclusions
- alertability rules

Defaults may live in `v2/config.json`, but runtime preferences belong in persistent configuration.

### Step C — Alertability

Introduce a clear distinction:

```
job relevance
      +
eligibility
      +
newness
      +
notification policy
      =
Telegram alert decision
```

Recommended default:

- explicit experience compatible with candidate
- configured maximum experience respected
- relevant role
- allowed geography
- not excluded
- genuinely new
- not previously alerted

Unknown experience should remain configurable rather than silently becoming an alert.

### Step D — Canonical identity and cross-source deduplication

The same job may appear on LinkedIn, Naukri and a company ATS. V2 now stores source observations separately and assigns them to canonical opportunities when identity evidence is strong enough. The current diagnostic endpoint exposes non-zero cross-source candidate pairs so merge policy can be validated on real data before lowering thresholds.

Current canonical implementation uses normalized company/location/title metadata, canonical URL normalization, experience corroboration, and description similarity. Strong cross-source matches are auto-linked; ambiguous company/title/location matches are intentionally kept separate. Distinct listings from the same source are never metadata-merged, preventing accidental collapse of separate requisitions.

The system must support:

- source identity
- company identity
- canonical job identity
- cross-source grouping

One opportunity should not generate multiple alerts.

### Step E — Telegram

Target alert:

```
🚨 94% MATCH

Software Engineer – AI
Company: XYZ
📍 Bengaluru
🕐 Posted 8 minutes ago
🔎 Discovered 2 minutes ago

✓ Software Engineer
✓ Python
✓ AI / LLM
✓ Bengaluru
✓ 2–3 years

Apply →
```

Telegram must be:

- new-only
- match-filtered
- deduplicated
- explainable
- direct-link based

### Step F — Frontend

Connect the existing dashboard to the V2 API.

Frontend should show:

- fresh jobs
- match score
- source
- company
- location
- posted time
- discovery time
- match reasons
- apply link
- source health
- configurable preferences

Do not prioritize visual polish over correctness.

### Step G — V1 shutdown

Only after V2 Telegram has proven reliable.

---

## 13. ENGINEERING RULES FOR FUTURE AGENTS

### Before changing a source

First inspect:

- structured/public interface
- pagination
- stable job IDs
- posting timestamp
- update timestamp
- rate limits
- failure modes

Prefer JSON/API over rendered HTML.

### Before increasing polling

Measure:

- requests/run
- jobs fetched/run
- relevant jobs/run
- new jobs/run
- 429/4xx/5xx rate
- median discovery lag

Never increase polling merely because a source returned zero jobs.

### Freshness

Always preserve:

- source posting time
- our discovery time
- precision of the source timestamp
- discovery latency when valid

Never invent exact times from date-only information.

### Matching

Keep geography and eligibility deterministic.

Do not use naive substring matching if it can create semantic false positives.

### Source failure isolation

One failing source must not stop other sources.

### Security

Never ask the user to paste:

- GitHub tokens
- SSH private keys
- Naukri passwords
- Telegram bot secrets

Use existing authenticated mechanisms and environment/secret storage.

### Applications

Never automate application submission.

Preserve canonical application links.

---

## 14. CURRENT IMPORTANT OBSERVATIONS

### Observation 1 — Ingestion is no longer the main blocker

LinkedIn and Naukri ingestion are working well enough to move into product-quality matching/notification work.

### Observation 2 — Matcher quality matters more than raw job count

The objective is not to maximize jobs stored.

The objective is to maximize the ratio:

```
worthwhile alerts / total alerts
```

Noise is a product failure.

### Observation 3 — Unknown data must remain unknown

If LinkedIn does not expose experience, do not manufacture one.

The system should represent uncertainty and make policy decisions from that explicit state.

### Observation 4 — Frontend configuration must be real

A UI control that only changes an old V1 config is not a V2 feature.

### Observation 5 — The current source roadmap is broader than the first three sources

The long-term goal includes useful ATS/career sources.

Do not expand source count aggressively until the core normalization, dedupe, matching, alerting and configuration architecture is solid.

---

## 15. WHAT NOT TO DO

Do not:

- restart Chromium scraping on Oracle for Naukri
- turn GitHub Actions into the primary scheduler
- rebuild V1 JSON-state architecture
- hardcode user preferences into Python
- send Telegram alerts before dedupe/newness checks
- treat every keyword hit as a good match
- invent posting timestamps
- increase source polling just because a source returns zero
- add AI matching before deterministic matching is reliable
- build elaborate frontend UI before alert quality is trustworthy
- disable V1 alerts before V2 Telegram works
- ask the user for credentials that are already configured on the VM

---

## 16. HOW TO UPDATE THIS DOCUMENT

This file is the project's durable handover.

**Update it whenever any of the following changes:**

- product goal
- target candidate profile
- source architecture
- source status
- infrastructure
- matching policy
- alerting policy
- frontend role
- important failure / lesson
- release checkpoint
- immediate next step

After a significant milestone, update the relevant section and especially:

- **Current release checkpoint**
- **Current important observations**
- **Immediate next steps**

Do not let the code and this document drift apart.

If a future agent discovers that this document contradicts the actual repository, the agent should:

1. inspect the repository
2. determine the actual current state
3. reconcile the document
4. only then continue development

---

## 17. HANDOVER SUMMARY FOR A NEW AGENT

If you have only a minute, read this section.

```
PRODUCT:
Personal always-on Job Radar.
Fresh jobs + accurate matching + low-noise Telegram alerts.

RUNTIME:
Oracle Always Free VM + Docker + SQLite.

LINKEDIN:
Direct ingestion from Oracle. Proven.

NAUKRI:
Do NOT scrape from Oracle.
Oracle systemd timer → GitHub workflow → Naukri → relay branch → V2.
Proven and running every 5 minutes.

INSTAHYRE:
Experimental; current probe returns HTTP 400.
Disabled by default.
Config-schema v3 migration makes it opt-in for legacy runtime configs.

V2:
Running on port 8000.
No Chromium.

MATCHER:
Initial false positives were fixed.
Current code uses phrase-aware matching and stricter experience handling.
Still being hardened for real alert quality.

CONFIG:
Current defaults are in v2/config.json.
Final requirement: preferences must be editable from frontend and persist on VM.
Preferred storage: /data/config.json.

TELEGRAM:
Not yet production-ready.
Must alert only on new + relevant + eligible + deduplicated jobs.

DEDUPLICATION:
Canonical opportunity layer is implemented conservatively.
Real LinkedIn/Naukri candidate validation remains before auto-link policy is broadened. The diagnostic now compares only shared normalized company/title families, avoiding expensive broad pair scans.

FRONTEND:
Repository dashboard now uses V2 local APIs.
Needs live browser/deployment verification.

V1:
Keep until V2 Telegram is proven; then disable duplicate V1 alerts.

NEXT:
Build V2 persistent configuration → configurable matcher/alertability → dedupe/newness → Telegram → frontend → disable V1.
```

---

## 18. SOURCE OF TRUTH HIERARCHY

When information conflicts, use this order:

1. **Actual deployed/repository code and observed runtime behavior**
2. **This handover document**
3. Older chat history / prototype notes

But when code changes intentionally, **update this document in the same milestone** so the next agent does not have to reverse-engineer the project again.

---

## 19. SUCCESS CRITERIA

Do not call Job Radar V2 successful merely because the API returns jobs.

V2 is successful when it can continuously:

1. detect fresh LinkedIn jobs repeatedly
2. detect fresh Naukri jobs repeatedly
3. preserve source posting and discovery timestamps separately
4. survive worker restarts without losing job history
5. identify genuinely new opportunities
6. deduplicate the same opportunity across sources
7. apply configurable deterministic preferences
8. reject obvious unsuitable jobs
9. provide explainable match reasons
10. send only worthwhile new matches to Telegram
11. expose the same useful information in the frontend
12. allow preference changes from the frontend without editing code
13. tolerate an individual source failing without taking down the radar

The final test is not "does it scrape?"

The final test is:

> **Can the user leave it running and trust that when Telegram rings, the job is probably worth opening?**


---

## 29. HISTORICAL DEBUGGING / OPERATIONS NOTES

These details are intentionally preserved because they explain why several architectural decisions must not be casually reversed.

### Oracle VM browser incident

The tiny Oracle VM previously reached approximately:

- load average ~15
- ~69% CPU steal
- ~13% iowait
- 208 zombie processes
- many Chromium / chrome_crashpad children

Stopping the old Docker runtime cleared the zombie buildup and returned the VM to a healthy idle state.

**Conclusion:** production V2 must remain browser-free unless there is compelling measured evidence otherwise.

### GitHub scheduler reliability

The project initially relied on frequent GitHub cron execution. Actual observed workflow history later showed long gaps, so a five-minute cron expression must not be described as guaranteed five-minute execution.

**Conclusion:** persistent scheduling belongs on the VM. GitHub Actions is a relay/acquisition worker where useful.

### V1 `seen.json` warning

V1 could add a rejected job to `seen.json`. This means a later configuration change could fail to reconsider it.

**Conclusion:** V2 must maintain separate observation/evaluation/alert state.

### GitHub CLI compatibility

The Ubuntu VM had an older GitHub CLI where `gh auth login --git-protocol ...` was unsupported. The working authentication path was:

```
gh auth login --hostname github.com --web
```

For run watching, use:

```
gh run watch <run-id> --repo AvinashBhalla/job-beeper --exit-status
```

Do not assume newer flags such as `--compact` exist.

---

## 30. DOCUMENTATION MAINTENANCE RULE

After every significant milestone, update:

- Current release checkpoint
- Current important observations
- Immediate next steps
- Source status
- Runtime/deployment status if changed

When a feature is visually present but backend-incomplete, mark it incomplete.

When a source is present in code but unverified, mark it unverified.

When a scheduler exists only manually on the VM, do not describe it as repository-reproducible.

The repository and this file should be kept in sync deliberately.
