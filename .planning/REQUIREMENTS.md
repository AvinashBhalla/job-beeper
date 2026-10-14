# Requirements: Job Radar

**Defined:** 2026-10-15
**Core Value:** Speed. Being the first applicant via almost 0-latency discovery.

## v1 Requirements

Requirements for the "Ultra-Fast" version.

### Platform Expansion
- [ ] **PLAT-01**: Support for a "Generic Adapter" that can fetch jobs from simple HTML/JSON feeds.
- [ ] **PLAT-02**: Integration of the user-provided niche platform list.
- [ ] **PLAT-03**: Isolation of platform failures so one slow/blocked site doesn't delay others.

### Real-Time Delivery
- [ ] **TIME-01**: Dashboard must update in real-time using SSE or WebSockets.
- [ ] **TIME-02**: Telegram notifications must be dispatched immediately upon discovery.
- [ ] **TIME-03**: End-to-end latency (Post $\rightarrow$ Notify) must be monitored and logged.

### Smart Filtering
- [ ] **FILT-01**: Filtering must happen *before* notification to ensure zero "noise".
- [ ] **FILT-02**: Filters must support complex role-family matching (e.g., SDE $\approx$ Software Engineer).

## v2 Requirements

Deferred to future release.

### Multi-User
- **USER-01**: User account system and individual filter profiles.
- **USER-02**: Per-user notification settings and channel management.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-Apply | High risk of account bans and poor quality applications |
| Proxy Rotation | Complexity and cost; prefer sustainable pacing |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLAT-01 | Phase 1 | Pending |
| PLAT-02 | Phase 2 | Pending |
| TIME-01 | Phase 1 | Pending |
| TIME-02 | Phase 1 | Pending |
| FILT-01 | Phase 1 | Pending |

---
*Requirements defined: 2026-10-15*
*Last updated: 2026-10-15 after initial definition*
