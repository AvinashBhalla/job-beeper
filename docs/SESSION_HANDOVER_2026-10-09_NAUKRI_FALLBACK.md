# Job Radar V2 — Session Handover (2026-10-09)

> Read this alongside `docs/JOB_RADAR_HANDOVER.md`. This note records the latest operational state and supersedes older statements in the main handover that say the public Naukri relay is not yet created or validated.

## Project and objective

- Private application repository: `AvinashBhalla/job-beeper`
- Active branch: `v2-live-radar`
- Production VM: Oracle Ubuntu host `job-radar`, project at `/home/ubuntu/job-beeper`
- Runtime: Docker Compose file `v2/docker-compose.yml`, service `radar`, port 8000, persistent SQLite.
- Public Naukri relay repository: `AvinashBhalla/job-beeper-naukri-relay`, default branch `main`; generated feed is on branch `naukri-relay`.
- Main priority: reliable fresh job discovery and accurate source-health/freshness measurement. Do not divert to dashboard redesign or new features until collection is reliable.

## LinkedIn: current state

The staggered LinkedIn collector has been deployed to the VM and observed in runtime logs. Latest evidence shared by the user:

```
linkedin discovery scan: queries=4 locations=4 requests=16 deep=True unique_jobs=86 failed_requests=0 elapsed=6.0s
linkedin: seen=86 new=0
linkedin discovery scan: queries=4 locations=4 requests=8 deep=False unique_jobs=53 failed_requests=0 elapsed=2.4s
linkedin: seen=53 new=0
linkedin discovery scan: queries=4 locations=4 requests=8 deep=False unique_jobs=49 failed_requests=0 elapsed=2.1s
linkedin: seen=49 new=0
```

Interpretation:
- The expected request reduction is live: 8 first-page targets per fast cycle; deep scan adds one page for those 8 targets (16 requests total in the normal case).
- Samples showed zero failed requests, but a few logs do not prove long-term absence of 429s.
- `new=0` means no new source records inserted in that scan; it does not mean no jobs were returned.
- Do not increase concurrency to address rate limiting. Continue observing at least 10–30 minutes of logs for `requests`, `failed_requests`, `elapsed`, `unique_jobs`, and `new`. If throttling returns, reduce request frequency/volume or use a permitted source; do not attempt access-control evasion.
- Relevant commits on `v2-live-radar`: stagger scan commit `f3be91d12388593869425913970232632744f6e0`; test fixture correction `fb9945d0ef30b85907945912bfaa9432729bf3ce`; latest docs correction `e937b9f98461250c72da2b5c334aefdf40b09339`. Latest known CI for the docs/test correction passed: https://github.com/AvinashBhalla/job-beeper/actions/runs/37915624743.

## Naukri public relay: verified facts

Feed URL:
https://raw.githubusercontent.com/AvinashBhalla/job-beeper-naukri-relay/naukri-relay/dashboard/data/naukri_relay.json

Latest feed inspection shared by user:
- `updated_at=2026-10-09T10:22:22.590629+00:00`
- `jobs=348`

Earlier inspection:
- `updated_at=2026-10-09T08:03:27.351028+00:00`
- `jobs=226`

The relay workflow's YAML on default branch `main` contains:
```yaml
on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch:
```

However, the GitHub Actions page showed only manually triggered runs. The workflow is active according to `gh workflow list`, and the YAML schedule is present, but automatic `schedule` events were not observed. Re-enabling it did not resolve the issue. Manual runs have succeeded.

## VM cron fallback: installed and trigger accepted

A fallback script was installed at:
`/home/ubuntu/job-beeper/scripts/trigger-naukri-relay.sh`

Log:
`/home/ubuntu/job-beeper/logs/naukri-relay-trigger.log`

Cron:
```cron
*/5 * * * * /home/ubuntu/job-beeper/scripts/trigger-naukri-relay.sh
```

The script:
- checks GitHub CLI auth;
- checks recent workflow runs and skips if a run is queued/in progress;
- uses a file lock to prevent overlapping trigger checks;
- triggers `gh workflow run naukri-relay.yml --repo AvinashBhalla/job-beeper-naukri-relay --ref main`;
- logs accepted/failed attempts.

Observed log:
```
2026-10-09T10:29:28+00:00 OK: relay workflow trigger accepted
```

GitHub showed a corresponding `workflow_dispatch` run in progress. This confirms that the VM fallback successfully submitted a trigger. It does **not** yet prove the run completed or that this specific run published a new feed.

Important: the latest status query still showed run #3 (created at 10:29:27 UTC) as `in_progress`, while the feed timestamp remained 10:22:22 UTC and count 348. The run ID #3 is the third relay run; query its exact ID from CLI rather than guessing. A previous command output showed scientific notation for IDs when using Go templates; prefer:
```bash
gh run list --repo AvinashBhalla/job-beeper-naukri-relay --limit 5 \
  --json databaseId,event,status,conclusion,createdAt --jq '.[]'
```
The specific numeric ID for the latest run was not confirmed in the latest user output. Do not reuse a guessed ID.

## Immediate next steps for the next agent

1. **Inspect the currently running relay workflow before changing anything.** Run:
   ```bash
   gh run list --repo AvinashBhalla/job-beeper-naukri-relay --limit 5 \
     --json databaseId,event,status,conclusion,createdAt --jq '.[]'
   ```
   Identify the run created at `2026-10-09T10:29:27Z`, then:
   ```bash
   gh run view <ACTUAL_NUMERIC_RUN_ID> --repo AvinashBhalla/job-beeper-naukri-relay --json status,conclusion,jobs,url
   gh run view <ACTUAL_NUMERIC_RUN_ID> --repo AvinashBhalla/job-beeper-naukri-relay --log
   ```
   If it is still running, find the slow step (collection, dependencies, or publishing). Don't alter the cron interval before identifying the bottleneck.
2. Once complete, check feed `updated_at` and `jobs`. Success requires the relay run to finish successfully **and** the feed timestamp to advance. A successful trigger alone is not success.
3. Check subsequent cron cycles in `~/job-beeper/logs/naukri-relay-trigger.log`. Ensure the fallback doesn't repeatedly trigger while a run is in progress and doesn't accumulate runs.
4. Verify the main app's Naukri source status after feed advancement; inspect `/api/source-status` and the container logs. Do not assume feed update means app ingestion succeeded.
5. Update this document with actual results, workflow run ID, feed timestamp/count, and source status. Do not mark success until these are observed.
6. Revisit Naukri discovery-latency measurement. Relay jobs often have date-only values like `"posted": "2026-10-09"`; the code currently sets `posted_precision="date"` but Naukri collector calculates `discovery_latency_seconds` whenever a parsed date has timezone info. Midnight UTC can be mistaken for exact posting time, inflating apparent latency. Correct the metric so date-only posting times are not represented as precise timestamps (use null or an explicit uncertainty interval), and add tests before claiming latency improvement.
7. Continue LinkedIn runtime measurement independently. Do not conflate Naukri relay scheduling with LinkedIn collection.

## Commands and gotchas

- On this VM's installed GitHub CLI, `gh run list --branch` is unsupported; don't use that flag.
- `workflowName` is not a supported `--json` field in this CLI. Use `name` if needed.
- Go template formatting of large `databaseId` values can print scientific notation; use `--jq '.[]' ` for exact numeric IDs.
- The placeholder `<RUN_ID>` is not a literal shell argument; replace it with the actual number.
- `gh workflow list` showed `public-naukri-relay active`. The workflow is not disabled.
- Do not disable or modify any existing systemd timer without checking the exact unit and its purpose first.
- Do not put PATs/secrets in chat, shell history, logs, or repository files.

## Definition of success

### Naukri relay
- VM fallback runs every five minutes while the VM is healthy.
- It avoids duplicate concurrent triggers.
- Relay runs finish successfully on consecutive cycles.
- Published feed timestamp advances on successful cycles and job count is nonzero.
- Last-good feed is preserved if collection fails or returns zero jobs.
- Main V2 app ingests the fresh feed and reports Naukri healthy.
- The date-only timestamp issue is corrected/tested so latency metrics do not falsely imply minute-level precision.

### LinkedIn
- Fast scans continue covering all configured query/location targets across two staggered cycles.
- Runtime logs show bounded requests and measured low failed/429 rates over a meaningful window.
- Fresh jobs reach the source DB/matcher promptly when visible from the source; evaluate with real timestamps rather than assuming polling cadence guarantees freshness.
- CI is green and the deployed container is confirmed to run the intended code.

### Handover quality
- Keep `docs/JOB_RADAR_HANDOVER.md` as the long-term product/architecture source of truth.
- Keep this file as the current operational incident handover; update both when a durable architecture decision changes.
- Never claim a run, deployment, source freshness, or acceptance criterion is successful without command/log evidence.
