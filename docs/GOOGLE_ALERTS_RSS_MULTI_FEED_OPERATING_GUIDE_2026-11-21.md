# Google Alerts RSS — multi-feed operating guide

**Date:** 21 November 2026  
**Repository:** `AvinashBhalla/job-beeper`  
**Implementation:** draft PR #101, branch `feat/google-alerts-rss-atom-parser`  
**Status:** implementation in draft; not deployed

## 1. Owner-confirmed format decision

All Google Alerts RSS feeds are expected to use the same Atom 1.0 output structure. What changes from alert to alert is the search/query text configured in Google Alerts; the feed-entry format and the JobBeeper processing contract remain the same.

This means:

- Use one parser, one poller, one queue schema, one safe destination fetcher and one shared ingestion path for every alert.
- Do not create per-query parsers, per-alert scrapers, different result schemas or separate job databases.
- Configure one feed record per Google Alert rule. Each rule's search string is already represented by the Google Alert that owns that feed; the RSS parser does not need to interpret or re-run the search string.
- A feed's stable opaque `id` links its checkpoint and entries to that alert. Its `label` is a non-secret operator-readable description. Its URL is the private bearer-like feed secret.
- The current loader intentionally accepts only `id`, `label` and `url`. Do not add a second query-language/configuration system unless a later product requirement proves it is necessary.

The owner expects the same output contract across all remaining alerts. A later feed that violates Atom 1.0 or the observed Google Alerts contract should be recorded as a sanitized feed error and investigated; do not silently route it through a different parser.

## 2. Current configuration contract

The protected runtime file has this shape (example values are placeholders only):

```json
{
  "feeds": [
    {
      "id": "alert-001",
      "label": "Software Engineering India",
      "url": "https://www.google.com/alerts/feeds/REDACTED/REDACTED"
    },
    {
      "id": "alert-002",
      "label": "React Node India",
      "url": "https://www.google.com/alerts/feeds/REDACTED/REDACTED"
    }
  ]
}
```

Rules:

- One item per RSS-enabled alert. The implementation currently caps this list at 98 feeds.
- IDs must be unique, stable, opaque strings. Do not derive IDs from or include the feed URL.
- Labels must be non-empty and non-sensitive; keep private search terms out of logs and public diagnostics.
- URLs must be Google Alerts HTTPS feed URLs matching the allowlisted host/path. Never include a feed URL in GitHub, issue text, PR comments, logs, terminal output or ChatGPT messages.
- The file path must be absolute and outside the repository. It must be a regular non-symlink file. POSIX group/other permission bits must be clear; use mode `0400` or `0600`.
- The file is plaintext protected by filesystem permissions; it is not encrypted. Mount/read it read-only where practical.
- The SQLite database stores opaque feed IDs, labels, validators/checkpoints, statuses and entry metadata. It must never store the feed URL.

The strict current shape is intentional. Query wording stays in Google Alerts and is not duplicated into the application config. The label is for safe operator recognition, not search semantics.

## 3. Shared processing flow

1. Load the complete enabled feed set from the owner-only configuration file.
2. Poll feeds sequentially through `poll_google_alerts_feed_batch()`. The default inter-request spacing is one second; persisted Retry-After deadlines are honored and one failed feed does not stop the rest of the batch.
3. Parse each feed through the same Atom 1.0 parser. The common entry output contains the Atom entry ID, title, snippet/content, destination URL, canonical URL and available published/updated timestamps.
4. Persist each feed's checkpoint and entries idempotently. A repeated Atom entry ID does not create a second queue row or reset an existing processing state.
5. Group entries by canonical destination URL. If different alert queries surface the same posting, fetch the destination once for the batch while retaining each alert/feed observation as provenance.
6. Fetch destination pages only through the bounded DNS-pinned HTTPS fetcher. Revalidate redirects, enforce robots.txt and response limits, and never use proxies, cookies, identity rotation or access-control bypasses.
7. Publish only when the conservative Schema.org JobPosting extractor has sufficient evidence (including title and hiring organization). Expired/blocked/insufficient pages are rejected, deferred or sent to review; an Alert snippet alone is not proof of a job.
8. Send verified records through existing V2 `normalize_job()` and `upsert_jobs()`. The shared jobs/canonical-opportunity store and existing per-member preference evaluations remain the single source of truth. Owner alert queries do not override member preferences.

A repeated posting found by several alert queries is one shared job with multiple observations, not multiple member-facing job records.

## 4. What exists in draft PR #101

- Atom 1.0 parsing, Google redirect unwrapping and canonical URL normalization.
- Protected external JSON config loader with a 98-feed cap and URL secrecy controls.
- Single-feed conditional polling and sequential multi-feed one-shot batch polling.
- ETag/Last-Modified support when the upstream supplies validators; HTTP 304 handling; bounded feed reads; Google-only redirect checks; Retry-After/backoff handling.
- SQLite feed checkpoint and entry-queue tables with idempotent writes.
- DNS-pinned HTTPS destination fetching, TLS hostname verification, per-hop DNS validation, robots.txt enforcement and bounded responses.
- Conservative Schema.org JobPosting extraction and a queue state model.
- Shared V2 normalization/upsert and existing per-user preference evaluation.

The current public code contract is `GoogleAlertsFeedConfig(feed_id, label, url)` and the loader accepts `{"feeds":[{"id":"...","label":"...","url":"..."}]}`.

Focused tests already cover the protected config loader, sequential batches, rate limits/backoff, idempotent checkpoints, multiple feed entries and canonical-URL grouping across alerts. The PR's reported isolated run is **73/73 focused tests passed**, with Python compilation passing on Python 3.10.12.

## 5. Important limits and non-goals

- The batch helper is a one-shot function, not a recurring scheduler. No timer, service schedule or production trigger has been added.
- The sample feed returned no ETag or Last-Modified header. Conditional requests may therefore save no bandwidth for this feed; do not assume all feeds provide validators.
- Google does not publish a guaranteed RSS availability or retention contract in the official Alerts help page. The observed feed window/cadence must be measured before selecting a polling interval.
- A 98-feed batch is not equivalent to a one-feed test. At the default one-second spacing, deliberate spacing alone adds roughly 97 seconds between the first and last request starts, excluding network time and any backoff. End-to-end batch duration can be materially longer.
- RSS delivery may be mutually exclusive with email delivery for an individual alert. Do not switch existing email alerts to RSS unless the owner deliberately accepts that delivery change and the coverage/retention pilot is satisfactory.
- No production database migration, feed-config installation, timer, production deployment, member notification change or Gmail/Pub/Sub setup is included.
- GitHub Actions quota is exhausted by owner choice. Do not trigger GitHub Actions runs, purchase minutes, enable billing or use paid hosted runners for this work.

## 6. No-cost validation and release sequence

1. **Isolated local validation:** use a fresh non-production checkout/worktree and virtual environment. Install only the repository's declared V2 development requirements in that isolated environment. Run the focused Google Alerts tests, then the complete V2 unittest suite. Do not install dependencies or run tests inside the production container/checkout or against the live database.
2. **Review evidence:** retain test commands, Python version, dependency versions, pass/fail counts and exact tested commit SHA in the handover. A missing dependency is a blocked test, not a passing test.
3. **Small multi-feed pilot:** configure a small number of owner-provided feeds (including the original and at least one other alert query) in a protected external file. Run the one-shot batch in an isolated database. Verify every feed is independently checkpointed, one feed failure does not stop others, and duplicate postings across alert queries collapse to one canonical job with both observations.
4. **Retention/cadence measurement:** compare repeated snapshots and observed entries over time to determine whether a chosen interval can safely capture new results. Record request count, duration, feed errors, Retry-After behavior, entry turnover and missed/duplicate items. Do not infer a global retention guarantee from one sample.
5. **98-feed pilot:** only after the small pilot and full V2 tests pass, load the full owner-approved feed set and run controlled one-shot batches against an isolated DB. Measure actual batch duration and request volume before adding any recurring timer.
6. **Release review:** document rollback, backups, schema migration, runtime config permissions, scheduler ownership, queue retention and monitoring. Production changes remain separate and require the applicable release gate/owner approval.

### Zero-cost test commands

Run these only in a disposable non-production worktree/virtual environment:

```bash
python -m pip install -r v2/requirements-dev.txt
python -m unittest v2.test_google_alerts_rss v2.test_google_alerts_rss_polling v2.test_google_alerts_safe_fetch v2.test_google_alerts_job_extract v2.test_google_alerts_pipeline -v
python -m unittest discover -s v2 -p 'test_*.py' -v
```

These are local commands and do not use GitHub Actions minutes. If dependencies cannot be installed in the isolated workspace, report the blocked suite precisely; do not claim full regression coverage.

## 7. Current status and owner input

| Area | Status |
|---|---|
| Common Atom parser and shared output contract | Implemented in draft PR #101 |
| Multiple feed config and sequential one-shot polling | Implemented in draft PR #101 |
| Per-feed checkpoints, retries and idempotency | Implemented in draft PR #101 |
| Safe destination verification and shared V2 ingestion | Implemented in draft PR #101 |
| Focused RSS tests | 73/73 passed in the reported isolated run |
| GitHub Actions CI | Not run/verified; do not spend quota |
| Complete V2 regression suite | Still unverified; prior clean workspace lacked `bs4` |
| Protected owner feed file / remaining feeds | Not supplied or installed |
| Retention/cadence pilot | Not done |
| Recurring scheduler | Not implemented/enabled |
| Production DB migration/deployment | Not done; production untouched |

**Nothing is required from the owner immediately.** Before the multi-feed pilot, the remaining private RSS feed URLs must be placed directly into the owner-only configuration file through an agreed secure file-transfer path. Do not paste the URLs into chat or commit them. Before migration of all rules, explicitly decide whether RSS should replace email delivery for those rules or whether separate email alerts must be preserved. The implementation work can continue with the existing sample and synthetic fixtures until then.
