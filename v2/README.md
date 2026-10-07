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

## API

- `GET /health`
- `GET /api/jobs?minutes=60`
- `GET /api/jobs/<id>`
- `GET /api/source-status`

The UI will be built only after live ingestion is proven.

## Run

```bash
pip install -r v2/requirements.txt
uvicorn v2.radar:app --host 0.0.0.0 --port 8000
```

For production, run the same process under Docker/systemd on a persistent VM. GitHub Actions is not the persistent monitoring engine; it is used only as the Naukri acquisition relay.
