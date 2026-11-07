# Job Radar V2 — live ingestion first

V2 is a clean rebuild of the failed V1. The first milestone is **fresh job discovery**, not dashboards, counts, scoring, or UI polish.

## Core rule

A job is not called "fresh" unless we record:

- source posting time when the source exposes it
- discovery time from our collector
- source + source job id
- discovery latency when both timestamps have enough precision

No synthetic timestamps are used to make a job look newer.

## Sources and polling

- **LinkedIn:** public guest jobs endpoint with a 180-second scheduling target, at least 4 seconds between global HTTP requests, two first-page search targets per scan, one JD-detail enrichment worker, and deep pagination every 30 minutes. Treat this as a lower-load measurement phase, not a guarantee that HTTP 429s are eliminated; source limits and search indexing mean target rotation makes discovery slower.
- **Naukri:** separate public relay feed, 300-second polling target. The relay preserves the external collection timestamp because acquisition happens on a GitHub-hosted runner.
- **Greenhouse:** public Job Board API, 900-second polling target, opt-in. The initial board registry is in `v2/config.json` (`greenhouse_boards`); the source is disabled by default until explicitly enabled through the preferences UI/API. The adapter requests `content=true` to capture full public job descriptions, scopes IDs by board token, isolates failures per board, and keeps jobs from successful boards if another board fails. The adapter uses `first_published` for original posting time when available, never substitutes `updated_at` (which can reflect later edits), and leaves posting time unknown when `first_published` is absent.
- **Instahyre:** 600-second polling target but disabled by default until its interface and freshness are verified.
- **Ashby:** public Job Posting API, 1800-second polling target, disabled by default. `ashby_boards` is an explicit allowlist seeded with OpenAI and PostHog; each request has a 15-second timeout, board failures are isolated, IDs are board-scoped, and posting timestamps come only from `publishedAt`.

The Greenhouse Job Board API documents unauthenticated GET endpoints for public board data and supports retrieving all job posts, with full descriptions available through the `content=true` query parameter: [official documentation](https://developers.greenhouse.io/job-board.html). Three board tokens are preconfigured after live API validation from the Oracle VM: `coinbase`, `gravitonresearchcapital`, and `zocdoc`. Edit `greenhouse_boards` in `v2/config.json` to add or remove employers; test each board's public API endpoint before enabling it. Each token is validated before it is used in the fixed Greenhouse API URL.

The collector remains deliberately low-volume. LinkedIn HTTP 429s stop the active search batch, activate a global cooldown with escalating 5/10/20/30-minute backoff and honor `Retry-After`; never add proxy/IP rotation, fake identities or CAPTCHA bypass to evade limits. Each new source feeds the same normalization, canonical opportunity linking, evaluation, alertability, notification ledger, and Telegram path. Source-specific failures must not stop other collectors, and date-only or unavailable posting timestamps must never be turned into invented freshness measurements. Free-first coverage improvement should prioritize permitted public ATS/company-career sources, one adapter at a time, before evaluating paid collection services.

## Storage

SQLite is intentional for the first hosted single-user deployment. It is durable on a persistent VM and removes the V1 JSON-file/git-commit feedback loop.

V2 now keeps source observations in `jobs` and canonical cross-source groupings in `canonical_opportunities`. Canonical linking is deliberately conservative: exact canonical URLs or strongly corroborated company/title/location matches may merge; ambiguous metadata matches remain separate.

## API

- `GET /health`
- `GET /api/jobs?minutes=60`
- `GET /api/jobs/<id>`
- `GET /api/source-status`
- `POST /api/auth/login` (public credential exchange; sets session and CSRF cookies)
- `GET /api/auth/me` (current authenticated account)
- `POST /api/auth/logout` (requires CSRF token)
- `GET /api/config` (admin session required)
- `PUT /api/config` (admin session + CSRF required)
- `GET /api/opportunities?minutes=60` (canonical opportunity groups)
- `GET /api/opportunities/<id>` (opportunity observations)
- `GET /api/dedupe-candidates?limit=100` (cross-source candidate diagnostics)

Runtime candidate preferences are still global and persisted at `/data/config.json`; only an authenticated `admin` can read or update them. Ordinary `user` accounts cannot access legacy job-feed, config, diagnostic or notification APIs until per-user preferences/evaluations are implemented. `/health` is public and returns only liveness metadata.

### Authentication and beta account provisioning

The current multi-user foundation uses SQLite tables `users`, `sessions`, `login_attempts` and `login_account_attempts`. Passwords use Argon2id. Browser sessions are opaque, seven-day cookies; only SHA-256 hashes of session and CSRF tokens are stored. Session cookies are HttpOnly, Secure by default and SameSite=Lax. State-changing admin requests require the CSRF cookie/header pair. All `/api/*` responses are marked `Cache-Control: no-store`. Login checks a same-origin `Origin` header when supplied (login-CSRF protection) and atomically reserves up to five attempts per email/IP and twenty attempts per account across all IPs in a 15-minute window. Email/IP keys are hashed in the throttle table, and malformed email values are throttled too; a successful login clears the reservation window.

There is no public signup endpoint. After deploying the feature to an isolated environment, create the first administrator from inside the app container (`WORKDIR /app`, `JOB_RADAR_DB=/data/jobs.db`):

```bash
python -m v2.auth_admin create-admin --email admin@example.com
python -m v2.auth_admin create-user --email beta-user@example.com
```

The first command creates only the first admin; the second creates an ordinary user and requires an admin to exist. Both prompt for the password twice with `getpass`; never put passwords in command-line arguments. `JOB_BEEPER_COOKIE_SECURE` defaults to `true` and requires HTTPS. The loopback-only `docker-compose.dev.yml` defaults it to `false` for SSH-tunnel development; never disable Secure on a public service. When TLS terminates at a reverse proxy and Uvicorn does not see the external scheme/host, set `JOB_BEEPER_PUBLIC_ORIGIN` to the exact browser-visible origin (for example, `https://jobs.example.com`) so login-Origin validation uses the public origin.

Per-user preferences and job evaluations are implemented on the current draft feature branch. Per-user Telegram account linking, default-off opt-in, a tenant-scoped delivery ledger, matching, deduplication and retry handling are implemented on the isolated feature branch; a real-bot HTTPS webhook and end-to-end delivery smoke test remain pending. Quiet hours, per-user time zones, configurable frequency controls, delivery history and server-side applications are future milestones. Keep the PR draft and do not treat these features as production-ready until review, CI and browser smoke tests are complete.

### Running the test suite

Install runtime and test-only dependencies, then run the complete V2 suite:

```bash
python -m pip install -r v2/requirements-dev.txt
python -m unittest discover -s v2 -p 'test_*.py' -v
```

The dashboard authentication contract tests use Node.js to exercise the cookie-session client, including protection against crafted cross-origin `?api=` URLs that could otherwise capture credentials. The GitHub V2 CI runner provides Node and installs the development requirements before running the full suite.

### Isolated Naukri relay

The main `AvinashBhalla/job-beeper` repository and application remain private. Naukri acquisition runs from a separate public relay-only repository, `AvinashBhalla/job-beeper-naukri-relay`. That repository should contain only the scheduled relay workflow, setup documentation and the generated feed on its `naukri-relay` branch; it must not contain or mirror the application source.

The public relay workflow checks out the private repository into a temporary runner directory and reads its `config.json` using a fine-grained `PRIVATE_APP_READ_TOKEN` secret with **Contents: read** permission limited to `AvinashBhalla/job-beeper`. The checkout is not committed to or published from the relay repository. Never paste the token into chat or commit it. The FastAPI container reads the generated JSON from the public raw URL, so the VM no longer needs a GitHub token. The public feed intentionally contains job postings and source URLs; do not publish credentials, runtime preferences or application configuration in the feed.

Do not deploy this consumer change until the public relay repository and its first successful feed publication have been verified. Once the public feed is live, stop the old VM timer that dispatches the private repository's relay workflow to avoid duplicate runs and private Actions-minute usage.

The dashboard is packaged with V2 and is served at `/dashboard/` by the FastAPI process. It reads jobs and settings from the V2 API rather than the legacy V1 GitHub JSON feed.

## Run

```bash
pip install -r v2/requirements.txt
uvicorn v2.radar:app --host 0.0.0.0 --port 8000
```

For production, run the same process under Docker/systemd on a persistent VM. GitHub Actions is not the persistent monitoring engine; it is used only as the Naukri acquisition relay.

## Multi-user preferences and personalized feed (feature branch)

The user-preferences milestone adds user_preferences and user_job_evaluations. New beta users start with empty preferences; they must save at least one target_roles entry and one locations entry before /api/jobs, /api/jobs/{job_id} or /api/daily-summary returns personalized data. The server derives ownership from the authenticated session and joins evaluations by user_id. The shared jobs, canonical_opportunities, source telemetry, global job_evaluations and notification_ledger remain shared/admin-owned in this milestone.

Authenticated endpoints:
- GET /api/preferences — current user's preferences and onboarding_complete.
- PUT /api/preferences — save the current user's preferences (CSRF required).
- GET /api/jobs — shared jobs with only the current user's match score/reasons; global notification details are withheld from normal users.
- GET /api/jobs/{job_id} — detail only when an evaluation row exists for the authenticated user.
- GET /api/daily-summary — shared discovered count and user-scoped match count. Normal users do not see global alert delivery counts.

Admin operational routes such as /api/config, source status, latency, dedupe, notification queue and LLM diagnostics remain admin-only. The first admin's legacy global candidate profile is migrated to that admin's preference row; new ordinary users never inherit it. Members can link one private Telegram chat through the one-time `/api/telegram/link` flow, then explicitly opt in through `/api/notifications/settings`. Per-user messages use a separate ledger and resolve only the current user's linked private chat; the legacy global admin notifier remains separate. Server-side applications remain a later milestone.

For isolated smoke testing, use v2/docker-compose.feature.yml (port 8002, separate radar-feature-data volume, all job source and LLM integrations disabled). Telegram and Google OAuth remain unconfigured by default and can be enabled only through a private, ignored .env.feature file; see docs/TELEGRAM_PER_USER_SETUP.md and docs/GOOGLE_OAUTH_SETUP.md. The feature-only seed command, python -m v2.seed_feature_demo, inserts four synthetic listings and refuses to run unless JOB_BEEPER_FEATURE_DEMO=true is set in the isolated feature container. See the root README's Multi-user feature smoke test section for PowerShell commands. This feature Compose project is separate from the existing dev service and must not be confused with a production rollout.


## Feed behavior and authenticated JobBeeper comparison (2026-11-07)

- Current member feed: GET /api/jobs?minutes=...&limit=...&q=...; keyword search is applied in SQLite before the result limit, with newest-first ordering. GET /api/jobs/{job_id} returns the current user's authorized job detail.
- Current dashboard request loads up to 500 jobs from the preceding 72 hours. Numeric page/per_page response metadata is not implemented yet; see docs/INGESTION_FIRST_ROADMAP.md for the planned backward-compatible pagination work.
- The dashboard refreshes the feed once per minute while visible and refreshes on tab return. Periodic feed/source-status requests are skipped while hidden.
- The authenticated JobBeeper comparison is in docs/JOBBEEPER_NETWORK_EVIDENCE_2026-11-07.md. Treat its observed request shapes as product evidence only, not an instruction to replay JobBeeper endpoints or copy private implementation details.
