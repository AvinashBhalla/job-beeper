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

This is a transitional security foundation, not full tenant isolation. Per-user preferences, evaluations, Telegram destinations/ledger and server-side applications are still future milestones. Do not invite ordinary beta users to use the job feed until those user-scoped features are implemented.

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
