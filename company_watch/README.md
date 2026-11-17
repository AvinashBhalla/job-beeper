# Isolated Company Watcher

This is a self-contained watcher added alongside JobBeeper. It does **not** import or call `v2.*`, read the JobBeeper SQLite database, change V2 runtime configuration, restart Docker, or modify existing collectors and notification workers.

## Safety defaults

- The Python CLI defaults to dry-run. Telegram is used only when an operator explicitly passes `--send`.
- The committed GitHub Actions workflow **always** runs `--dry-run`; it does not reference or receive Telegram secrets.
- The workflow has `contents: read` permission. It never commits scan state to `main` or another Git branch.
- Deduplication state is stored in a separate GitHub Actions cache scoped to the workflow branch. The report is uploaded as a short-lived Actions artifact.
- The watcher has its own `company_watch/.state/` directory, excluded by `.gitignore`.

## Company registry

`companies.csv` contains all 100 source rows and has a populated `careers_url` for each. Each row also records `scan_mode`, `scan_enabled`, and `verification_status`.

- 90 rows are enabled for initial dry-run scanning.
- 10 rows are held for manual review or exact identity/board confirmation. Some have an official homepage, a partial entity match, or a research-only search pointer. These are not fetched by the workflow.
- A populated URL does not mean every site exposes a machine-readable job board. Generic career pages may only yield `review` candidates until structured JobPosting data or a supported ATS adapter is available.
- 26 original career URLs were retained from the updated user-supplied CSV and are marked `provided_url_needs_live_validation`; a successful dry-run request is the next verification step.

Do not convert search pointers or an entity ambiguity into an automatically scanned URL. Confirm the employer identity and update the row's `scan_enabled` only after the official board is verified.

## Supported collection

- Greenhouse public Job Board API
- Lever public postings API
- Ashby public posting API
- SmartRecruiters public posting API
- Generic official career pages: JSON-LD `JobPosting` first, then conservative link-only leads marked `review`

Workday, Workable and other dynamic career sites that are not backed by an implemented adapter are held for review rather than guessed or scraped aggressively.

## Run locally

```bash
python -m pip install -r company_watch/requirements.txt
python company_watch/scan.py --dry-run --report-json /tmp/company-watch-report.json
```

To persist a local dry-run baseline intentionally:

```bash
python company_watch/scan.py --dry-run --remember-dry-run --state-file company_watch/.state/seen.json
```

The workflow does this using an isolated Actions cache. It does not write to Git.

## Schedule

After the pull request is merged into the repository's default branch, the workflow runs at 08:00, 14:00 and 21:00 IST, and can also be manually dispatched. GitHub scheduled workflows run from the default branch, so the schedule will not become active while this remains only a feature branch.

## Telegram later (not enabled)

The scanner supports the existing secret aliases `TG_TOKEN` / `TG_CHAT_ID` and `JOB_RADAR_TELEGRAM_BOT_TOKEN` / `JOB_RADAR_TELEGRAM_CHAT_ID` only for a future explicit `--send` run. No secrets are referenced by the committed workflow. Do not paste credentials into code, CSV, issues, pull requests or chat. Enabling sends requires a separate reviewed change after dry-run quality is accepted.