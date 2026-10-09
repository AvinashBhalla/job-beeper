# Job Radar V2

The active production application is the V2 service on the `v2-live-radar` branch. It runs on an Oracle Cloud Ubuntu VM using Docker Compose and SQLite persistence. Do not use the older `main` branch as the deployment source for V2; `main` is behind the active release branch and still describes the earlier static-dashboard implementation.

## Current production path

- **App:** FastAPI service in `v2/radar.py`.
- **Runtime:** `v2/docker-compose.yml`; service `radar`, port 8000.
- **Persistent data:** Docker volume `radar-data`, SQLite at `/data/jobs.db`, runtime preferences at `/data/config.json`.
- **Collectors:** LinkedIn, Naukri (from a separate public relay), Instahyre (disabled), Greenhouse (disabled pending ingestion-safety validation).
- **Pipeline:** normalize → upsert → canonical dedupe → match/evaluate → freshness and alertability policy → notification ledger → Telegram.
- **Naukri relay:** [separate repository](https://github.com/AvinashBhalla/job-beeper-naukri-relay). Do not confuse it with the legacy `naukri-relay` branch in this repository.

## Start / inspect

```bash
sudo docker compose -f v2/docker-compose.yml ps
curl -fsS http://127.0.0.1:8000/health
sudo docker compose -f v2/docker-compose.yml logs --tail=100 radar
```

Runtime preferences are protected by the `X-Config-Token` header. Retrieve the token only on the VM from `/data/config_token`; never print it to chat or commit it.

## Knowledge transfer

- **Current state, branch map, blockers, next work, release checklist:** [Job Radar V2 Knowledge Transfer](docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md)
- **Chronological engineering history:** [Job Radar Handover](docs/JOB_RADAR_HANDOVER.md)
- **V2 implementation notes:** [V2 README](v2/README.md)
- **Public JobBeeper behavior reference:** [JobBeeper Reference](docs/JOBBEEPER_REFERENCE.md)

## Branch policy

Branch all production V2 work from `v2-live-radar`, merge tested changes back into it, and deploy only after CI passes. Keep `main` until the repository's default-branch/promotion decision is made separately. Delete topic branches after their PRs merge; do not delete the production branch or the separate relay repository.
