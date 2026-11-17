# Job Radar

## Current engineering priority — 17 November 2026

The active priority is fetcher and feed reliability: source polling, ATS board scheduling, rate-limit control, pagination, normalization, deduplication, freshness and dashboard visibility. Telegram is optional; users can collect, match and view jobs without linking Telegram. Telegram is only needed when users choose it for notification delivery and opt in. Member-only enhancements and Company Watch expansion are deferred until the current feed is dependable. See the [Fetcher and Feed Reliability Plan](docs/FETCHER_AND_FEED_RELIABILITY_PLAN_2026-11-17.md).


JobBeeper is evolving into an end-to-end job-search product: discover relevant jobs, evaluate fit and freshness, prepare truthful applications, track progress, and support referrals and follow-ups. Its shared ingestion engine feeds user-scoped matching and notifications; resume assets, applications and outreach remain private to each user.

## Branch and VM model

- **`main` = production release branch.**
- **`v2-live-radar` = development/integration branch.** Develop and validate changes here first; promote tested releases to main through a reviewed PR.
- **VM rollout status:** GitHub main promotion is complete, but Oracle currently still runs the existing checkout/container from `v2-live-radar`. Do not claim production has switched until the controlled cutover and smoke tests are complete.
- Target VM layout: `/home/ubuntu/job-beeper` will become the production checkout on `main`; `/home/ubuntu/job-beeper-dev` is the isolated development checkout on `v2-live-radar`.

## Production service

- Compose file: `v2/docker-compose.yml`
- Production host port: `8000`
- Database: persistent Docker volume mounted at `/data`, with SQLite at `/data/jobs.db` and runtime preferences at `/data/config.json`.
- Preserve the existing Compose project and volume during the production branch switch; do not bring production down with `down -v`.
- Start/inspect:
  ```bash
  sudo docker compose --env-file .env -f v2/docker-compose.yml ps
  curl -fsS http://127.0.0.1:8000/health
  sudo docker compose --env-file .env -f v2/docker-compose.yml logs --tail=100 radar
  ```

## Isolated development service

- Compose file: `v2/docker-compose.dev.yml`; safe defaults: `v2/config.dev.json`.
- Loopback-only host port: `8001`; use an SSH tunnel to view it from your computer.
- Independent database volume: `job-radar-dev_radar-dev-data`; independent generated config and config token.
- Dev defaults: Naukri relay ingestion only; LinkedIn, Instahyre and Greenhouse disabled; Telegram notifications disabled and credentials blank. This keeps dev data separate, prevents test notifications, and avoids doubling LinkedIn requests/raising its 429 risk.
- The development Compose file needs the VM-local ignored `.env` explicitly supplied: host-side checks showed that Compose's default dotenv discovery did not resolve `GEMINI_API_KEY`, while `--env-file .env` did. These commands must run only from an account/session already authorized to access the Docker socket; do not use `sudo` or weaken socket/group permissions as a workaround.
- Before any create/recreate/restart, verify the existing dev container and actual `/data` volume mapping so the named `job-radar-dev_radar-dev-data` database is not replaced or confused with production. The current handover records the pending verification gate.
- Build/start from the dev clone root **only after the volume and running environment have been verified by an authorized Docker operator**:
  ```bash
  docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build
  docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml ps
  curl -fsS http://127.0.0.1:8001/health
  ```
- View logs:
  ```bash
  docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml logs --tail=100 radar
  ```
- The local `.env` stores a Gemini key only if the user supplies one; never print/commit it. Keep both `GEMINI_EXTRACTION_ENABLED` and `GEMINI_MATCHER_ENABLED` false until the initial controlled checks are complete.
- From Windows PowerShell, forward the existing dev port with `ssh -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197`, keep that terminal open, then run `Start-Process "http://127.0.0.1:18001/dashboard/"` in a second PowerShell window. Check health with `Invoke-RestMethod "http://127.0.0.1:18001/health" | ConvertTo-Json -Depth 5`. If SSH needs a key/alias, retain the same options as the user's working SSH command.
- The currently running dev container is an older build and does **not** yet include merged PR #45. Do not use the existing dev database for the new auth/multi-user migration until a separate feature-test environment and verified DB copy are prepared.
- Never add production Telegram credentials to the dev Compose file. Enable source collectors in dev only deliberately; do not enable LinkedIn while production is querying it unless conducting a coordinated rate-limit test.

## Sources and pipeline

- **LinkedIn:** low-volume guest-job requests with a 180-second scheduler target, 4-second minimum request spacing, global stop-on-429, Retry-After support and escalating 5/10/20/30-minute cooldowns. These measures reduce pressure; they do not guarantee that 429 never recurs.
- **Naukri:** separate [public relay repository](https://github.com/AvinashBhalla/job-beeper-naukri-relay), polled by both environments; the app instances maintain separate databases.
- **Greenhouse:** public Job Board API, opt-in and disabled until the single-board canary passes ingestion/dedupe/timestamp tests.
- **Instahyre:** disabled until interface and freshness are verified.

Runtime candidate preferences remain global and are admin-only until the in-progress per-user preferences milestone is merged and tested. The V2 browser now uses server-side cookie sessions: Argon2id passwords, HttpOnly/Secure/SameSite=Lax session cookies, CSRF validation for writes, no-store API responses, five attempts per email/IP plus twenty account-wide attempts across IPs per 15 minutes, same-origin login routing, and admin-only access to legacy global APIs. The old config-token helper remains in the backend for compatibility but is no longer used by the dashboard. If TLS terminates at a reverse proxy and Uvicorn sees an internal origin, set `JOB_BEEPER_PUBLIC_ORIGIN` to the exact public dashboard origin. See [V2 authentication and account provisioning](v2/README.md#authentication-and-beta-account-provisioning) before enabling accounts; ordinary users must not be given feed access in a deployed environment until PR #46 is reviewed, merged, smoke-tested and released.

## Handover and product reference

- **Current status, next task and release checklist:** [Job Radar V2 Knowledge Transfer](docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md)
- **Chronological engineering history:** [Job Radar Handover](docs/JOB_RADAR_HANDOVER.md)
- **V2 implementation notes:** [V2 README](v2/README.md)
- **Product vision, architecture decisions and delivery priorities:** [Product Vision and Delivery Roadmap](docs/PRODUCT_VISION_AND_DELIVERY_ROADMAP.md)
- **Reference repository research:** [Career-Ops and Apply Factory findings](docs/REFERENCE_REPOSITORIES_RESEARCH_2026-11-08.md)
- **Product behavior and source roadmap:** [JobBeeper Reference](docs/JOBBEEPER_REFERENCE.md)

Mandatory process: update both handover files after every user prompt, directly on `v2-live-radar` for working-state documentation. Do not create a separate branch solely for docs. Code and config changes require tests; promote to `main` only when verified.

## Multi-user feature smoke test (isolated from the existing dev service)

The current multi-user feature branch has its own disposable Compose file, loopback port **8002**, and independent Docker volume. It disables all collectors, Telegram and LLM providers. It does not share the existing job-radar-dev database on port 8001 or production on port 8000.

Run these from Windows PowerShell after the feature branch is pushed to the VM worktree:

~~~powershell
# Build/start the isolated feature container (does not touch ports 8000 or 8001)
ssh ubuntu@130.210.27.197 "cd /tmp/job-radar-user-preferences && sudo docker compose -p job-radar-user-preferences -f v2/docker-compose.feature.yml up -d --build"

# Bootstrap the first admin; the CLI prompts for a password interactively
ssh -t ubuntu@130.210.27.197 "cd /tmp/job-radar-user-preferences && sudo docker compose -p job-radar-user-preferences -f v2/docker-compose.feature.yml exec radar python -m v2.auth_admin create-admin --email YOUR_ADMIN_EMAIL"

# Create a separate beta test account; it starts with empty role/location preferences
ssh -t ubuntu@130.210.27.197 "cd /tmp/job-radar-user-preferences && sudo docker compose -p job-radar-user-preferences -f v2/docker-compose.feature.yml exec radar python -m v2.auth_admin create-user --email YOUR_TEST_USER_EMAIL"

# Seed four clearly synthetic listings so the personalized feed can be tested without scraping
ssh ubuntu@130.210.27.197 "cd /tmp/job-radar-user-preferences && sudo docker compose -p job-radar-user-preferences -f v2/docker-compose.feature.yml exec radar python -m v2.seed_feature_demo"

# Terminal 1: open and keep this tunnel running
ssh -L 18002:127.0.0.1:8002 ubuntu@130.210.27.197

# Terminal 2: health check and dashboard
Invoke-RestMethod "http://127.0.0.1:18002/health" | ConvertTo-Json -Depth 5
Start-Process "http://127.0.0.1:18002/dashboard/"
~~~

Sign in as the test user. For a predictable demo match, enter Python Developer and Bengaluru (the seed script adds four synthetic jobs). The onboarding form must require both a target role and a target location; after saving, the user sees only their personalized matching feed. Demo listings use example.com URLs and are not real vacancies. The admin account uses the legacy admin dashboard and controls. Do not paste passwords into chat or put them in command arguments.

Stop the isolated feature container without deleting its test database:

~~~powershell
ssh ubuntu@130.210.27.197 "cd /tmp/job-radar-user-preferences && sudo docker compose -p job-radar-user-preferences -f v2/docker-compose.feature.yml down"
~~~

The feature image has been built and the Compose file validated, but the feature container has not been started. The feature environment's radar-feature-data volume is intentionally preserved by down; do not add -v unless you explicitly want to erase the isolated test database. This is a user-run smoke-test environment, not a production deployment.
