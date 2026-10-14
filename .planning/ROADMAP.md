# Roadmap: Job Radar

## Phase 1: The Real-Time Core
**Goal:** Transform the system from "Fast Polling" to "Real-Time Feel".

- **Plan 1: Live Dashboard Infrastructure**
    - Implement SSE (Server-Sent Events) in FastAPI to push new jobs to the UI.
    - Update `app.js` to listen for events and prepend jobs to the feed.
- **Plan 2: Notification Pipeline Optimization**
    - Ensure `deliver_queued_notifications` is triggered immediately after `upsert_jobs`.
    - Audit `notification_ledger` for any delays.
- **Plan 3: Generic Adapter Framework**
    - Create a base `SourceAdapter` class to standardize how new platforms are added.

## Phase 2: The Niche Expansion
**Goal:** Massively increase coverage using the user's researched list.

- **Plan 1: Niche Platform Integration**
    - Implement adapters for the provided list of niche sites.
    - Configure polling intervals based on each site's volatility.
- **Plan 2: Latency Monitoring**
    - Add a "Latency Dashboard" view to see which platforms are slowest.

## Phase 3: Hardening & Polish
**Goal:** Ensure stability as the number of sources grows.

- **Plan 1: Error Handling & Circuit Breaking**
    - Implement circuit breakers for failing niche sites to prevent resource exhaustion.
- **Plan 2: Performance Audit**
    - Optimize SQLite queries for the growing `jobs` table.

---
**Success Criteria:**
- New jobs appear on the dashboard within < 1s of discovery.
- Telegram notifications arrive within < 2s of discovery.
- Niche platforms integrated without breaking LinkedIn stability.
