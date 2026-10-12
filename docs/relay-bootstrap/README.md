# JobBeeper Naukri Relay

This repository is intentionally separate from the private JobBeeper application. Its public contents are limited to the scheduled collector workflow, this setup note, and the generated feed on the `naukri-relay` branch.

## Setup

1. Keep this repository public so GitHub-hosted Actions runs use the public-repository runner allowance.
2. Add a repository secret named `PRIVATE_APP_READ_TOKEN`. Use a fine-grained token restricted to `AvinashBhalla/job-beeper` with **Contents: read** only.
3. Add `.github/workflows/naukri-relay.yml` from this setup's workflow file.
4. Run the workflow once manually and verify `dashboard/data/naukri_relay.json` exists on the `naukri-relay` branch and includes `updated_at`, `count`, and a non-empty `jobs` array.
5. The private app consumes the raw feed anonymously from:
   `https://raw.githubusercontent.com/AvinashBhalla/job-beeper-naukri-relay/naukri-relay/dashboard/data/naukri_relay.json`

## Privacy and reliability

- Do not copy the private app, database, user configuration, tokens, or secrets into this repository.
- The workflow checks out only `v2/config.json` from the private repository.
- An empty collection fails rather than overwriting the last-good feed.
- Job data is intentionally public in the generated feed.
- Scheduled execution is every five minutes; GitHub cron is best-effort and can be delayed.
