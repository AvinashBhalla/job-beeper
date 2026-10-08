# Job Radar V2 — live ingestion first

V2 is a clean rebuild of the failed V1. The first milestone is **fresh job discovery**, not dashboards, counts, scoring, or UI polish.

## Core rule

A job is not called "fresh" unless we record:

- source posting time when the source exposes it
- discovery time from our collector
- source + source job id
- discovery latency when both timestamps have enough precision

No synthetic timestamps are used to make a job look newer.

## First sources

1. LinkedIn public guest jobs endpoint — 2 minute polling target
2. Naukri via the existing GitHub-hosted relay — 2 minute relay polling target
3. Instahyre — 10 minute polling target, initially treated as experimental until freshness is verified

The collector is deliberately small and low-volume. LinkedIn's guest endpoint currently exposes logged-out job cards and supports recency filtering. Naukri is acquired by the existing GitHub-hosted watcher and published as a relay feed because direct Naukri access from the Oracle VM is timing out. The relay preserves source posting data and its collection timestamp.

## Storage

SQLite is intentional for the first hosted single-user deployment. It is durable on a persistent VM and removes the V1 JSON-file/git-commit feedback loop.

V2 now keeps source observations in `jobs` and canonical cross-source groupings in `canonical_opportunities`. Canonical linking is deliberately conservative: exact canonical URLs or strongly corroborated company/title/location matches may merge; ambiguous metadata matches remain separate.

## API

- `GET /health`
- `GET /api/jobs?minutes=60`
- `GET /api/jobs/<id>`
- `GET /api/source-status`
- `GET /api/config`
- `PUT /api/config` (requires `X-Config-Token`)
- `GET /api/opportunities?minutes=60` (canonical opportunity groups)
- `GET /api/opportunities/<id>` (opportunity observations)
- `GET /api/dedupe-candidates?limit=100` (cross-source candidate diagnostics)

Runtime user preferences are persisted at `/data/config.json`. The configuration API is protected by a generated token stored at `/data/config_token`, unless `JOB_RADAR_CONFIG_TOKEN` is supplied to the container.

The dashboard is packaged with V2 and is served at `/dashboard/` by the FastAPI process. It reads jobs and settings from the V2 API rather than the legacy V1 GitHub JSON feed.

## Run

```bash
pip install -r v2/requirements.txt
uvicorn v2.radar:app --host 0.0.0.0 --port 8000
```

For production, run the same process under Docker/systemd on a persistent VM. GitHub Actions is not the persistent monitoring engine; it is used only as the Naukri acquisition relay.
