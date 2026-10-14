# Job Radar: Zero-Latency Job Aggregator

## What This Is

A high-performance job discovery engine designed to minimize the gap between a job being posted and the user applying. It aggregates listings from giants (LinkedIn, Naukri) and niche platforms in real-time, filtering them against strict user criteria to provide instant notifications via Telegram and a live dashboard.

## Core Value

**Speed is the product.** The system ensures the user is among the first applicants by achieving near-zero discovery latency and instant alert delivery.

## Requirements

### Validated
- ✓ Job discovery from LinkedIn (Guest API) — v2
- ✓ Job discovery from Naukri (Relay) — v2
- ✓ Job discovery from Greenhouse/Ashby (ATS APIs) — v2
- ✓ Telegram notification delivery — v2
- ✓ Basic job matching/filtering (Role, Skills, Location, Exp) — v2
- ✓ Fast-lane polling for LinkedIn (180s) — v2

### Active
- [ ] **Generic Platform Adapter**: A flexible system to integrate niche platforms quickly without writing custom scrapers for every single site.
- [ ] **Live-Push Dashboard**: Transition from a request-response dashboard to a real-time feed (SSE/WebSockets) so jobs appear instantly without refresh.
- [ ] **Latency Benchmarking**: Precise tracking of "Post Time" vs "Notify Time" to identify and eliminate bottlenecks.
- [ ] **Dynamic Niche Integration**: Implementation of the custom platform list provided by the user.

### Out of Scope
- **Multi-user support** — Currently designed for a single user; expansion to a public SaaS is a future milestone.
- **Automatic Applying** — The tool focuses on discovery and notification, not automated application submission.

## Context

The project is an evolution of "Job Radar V2". It uses a FastAPI backend with SQLite for durability. It specifically handles the "cat-and-mouse" game of LinkedIn rate limits (HTTP 429) using an escalating cooldown strategy.

## Constraints

- **Rate Limits**: Must honor source limits to avoid IP bans (especially LinkedIn).
- **Precision**: Discovery timestamps must be authoritative; no synthetic "freshness".
- **Tech Stack**: Python (FastAPI), SQLite, Telegram Bot API.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite Storage | Simplicity and durability for single-user deployment. | ✓ Good |
| LinkedIn Pacing | 180s polling + 4s interval to prevent 429s. | ✓ Good |
| Guest Endpoints | Using public guest APIs where possible to avoid account bans. | ✓ Good |

---
*Last updated: 2026-10-15 after project initialization*
