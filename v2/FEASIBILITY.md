# V2 feasibility checkpoint — 2026-10-07

## LinkedIn

**Promising for live discovery.**

The logged-out guest jobs endpoint is still being documented and used by current 2026 projects:

- `/jobs-guest/jobs/api/seeMoreJobPostings/search`
- returns HTML job cards
- current independent documentation reports 10 cards per response
- relative posting age is available in the card
- a job-detail guest endpoint is also available

The collector therefore polls newest-first with a short recency window, keeps a wider six-hour safety window to survive a missed cycle, and records the source-relative posting time separately from our discovery time.

We are deliberately keeping request volume low and backing off on 429/5xx responses.

## Naukri

**Promising but less stable.**

The current JobSpy Naukri adapter uses Naukri's `/jobapi/v3/search` endpoint and generates the current `nkparam` request token. Current 2026 source code shows this path is still active.

The important limitation is timestamp precision: Naukri search results may expose a date without an exact posting time. V2 will not manufacture an exact "posted 7 minutes ago" value from a date-only field.

If the live environment starts returning 406/403 or otherwise becomes unreliable, we will add the browser-based collector rather than silently showing stale results.

## Instahyre

**Experimental until measured.**

The public JSON path used by V1 is still kept as a probe, but we are not treating it as a reliable real-time source until repeated runs prove that it exposes current postings and usable timestamps.

## Hosting

GitHub Actions is **not** the runtime.

For a genuinely persistent free worker, Oracle Cloud's Always Free compute is the current practical fit: Oracle documents Always Free AMD micro instances and Ampere A1 compute resources, including up to 2 OCPUs and 12 GB RAM for the A1 allowance.

Render/Koyeb free services are not suitable as the continuous worker: Render free web services sleep after 15 minutes of inactivity and free background workers are not available; Koyeb's free instance cannot be used as a Worker Service and scales to zero.

The V2 repo therefore includes Docker + a cloud-init bootstrap for a persistent VM.

## Release gate

We do not call V2 successful until the deployed process proves:

1. LinkedIn fresh jobs are detected repeatedly.
2. Naukri fresh jobs are detected repeatedly.
3. Discovery time is persisted independently of source posting time.
4. A restarted worker resumes from the database without losing prior jobs.
5. The feed can show jobs discovered in the last hour without a manual scan.

Only after those pass do we build matching, Telegram, and UI.
