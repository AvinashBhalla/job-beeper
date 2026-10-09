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

- **LinkedIn:** public guest jobs endpoint, 60-second scheduling target with conservative rotating query/location coverage.
- **Naukri:** separate public relay feed, 300-second polling target. The relay preserves the external collection timestamp because acquisition happens on a GitHub-hosted runner.
- **Greenhouse:** public Job Board API, 900-second polling target, opt-in. The initial board registry is in `v2/config.json` (`greenhouse_boards`); the source is disabled by default until explicitly enabled through the preferences UI/API. The adapter requests `content=true` to capture full public job descriptions, scopes IDs by board token, isolates failures per board, and keeps jobs from successful boards if another board fails. Greenhouse's documented `updated_at` value is not assumed to be the original posting timestamp; the adapter leaves posting time unknown unless a true posting field is exposed.
- **Instahyre:** 600-second polling target but disabled by default until its interface and freshness are verified.

The Greenhouse Job Board API documents unauthenticated GET endpoints for public board data and supports retrieving all job posts, with full descriptions available through the `content=true` query parameter: [official documentation](https://developers.greenhouse.io/job-board.html). Three board tokens are preconfigured after live API validation from the Oracle VM: `coinbase`, `gravitonresearchcapital`, and `zocdoc`. Edit `greenhouse_boards` in `v2/config.json` to add or remove employers; test each board's public API endpoint before enabling it. Each token is validated before it is used in the fixed Greenhouse API URL.

The collector remains deliberately low-volume. Each new source feeds the same normalization, canonical opportunity linking, evaluation, alertability, notification ledger, and Telegram path. Source-specific failures must not stop other collectors, and date-only or unavailable posting timestamps must never be turned into invented freshness measurements.

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
