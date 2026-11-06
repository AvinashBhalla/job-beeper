# Job Radar

Job Radar is a personal, always-on job discovery and matching service. Its pipeline is source-specific ingestion → normalization and canonical deduplication → deterministic preference matching → a persisted notification ledger → dashboard and Telegram.

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
- On the developer's computer, forward the port with `ssh -L 8001:127.0.0.1:8001 ubuntu@<VM_HOST>`, then open `http://127.0.0.1:8001/dashboard/`.
- Never add production Telegram credentials to the dev Compose file. Enable source collectors in dev only deliberately; do not enable LinkedIn while production is querying it unless conducting a coordinated rate-limit test.

## Sources and pipeline

- **LinkedIn:** low-volume guest-job requests with a 180-second scheduler target, 4-second minimum request spacing, global stop-on-429, Retry-After support and escalating 5/10/20/30-minute cooldowns. These measures reduce pressure; they do not guarantee that 429 never recurs.
- **Naukri:** separate [public relay repository](https://github.com/AvinashBhalla/job-beeper-naukri-relay), polled by both environments; the app instances maintain separate databases.
- **Greenhouse:** public Job Board API, opt-in and disabled until the single-board canary passes ingestion/dedupe/timestamp tests.
- **Instahyre:** disabled until interface and freshness are verified.

Runtime candidate preferences remain global and are admin-only. The V2 browser now uses server-side cookie sessions: Argon2id passwords, HttpOnly/Secure/SameSite=Lax session cookies, CSRF validation for writes, no-store API responses, five attempts per email/IP plus twenty account-wide attempts across IPs per 15 minutes, same-origin login routing, and admin-only access to legacy global APIs. The old config-token helper remains in the backend for compatibility but is no longer used by the dashboard. If TLS terminates at a reverse proxy and Uvicorn sees an internal origin, set `JOB_BEEPER_PUBLIC_ORIGIN` to the exact public dashboard origin. See [V2 authentication and account provisioning](v2/README.md#authentication-and-beta-account-provisioning) before enabling accounts; ordinary users must not be given feed access until per-user preferences/evaluations are implemented.

## Handover and product reference

- **Current status, next task and release checklist:** [Job Radar V2 Knowledge Transfer](docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md)
- **Chronological engineering history:** [Job Radar Handover](docs/JOB_RADAR_HANDOVER.md)
- **V2 implementation notes:** [V2 README](v2/README.md)
- **Product behavior and source roadmap:** [JobBeeper Reference](docs/JOBBEEPER_REFERENCE.md)

Mandatory process: update both handover files after every user prompt, directly on `v2-live-radar` for working-state documentation. Do not create a separate branch solely for docs. Code and config changes require tests; promote to `main` only when verified.
