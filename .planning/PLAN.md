# Phase 1 Plan: The Real-Time Core (v2 - Hardened)

**Goal:** Transform the system from "Fast Polling" to "Real-Time Feel" with zero-risk concurrency.
**Requirements Covered:** TIME-01, TIME-02, PLAT-01, FILT-01.

---

## 🏗️ Architectural Changes

### 1. Thread-Safe Real-Time Bridge (SSE)
- **Pattern:** `Sync-Thread` $\rightarrow$ `Async-Queue` $\rightarrow$ `SSE-Stream`.
- **Implementation:**
    - Create `ConnectionManager` in `v2/radar.py`.
    - Use `asyncio.Queue` for each client.
    - Use `loop.call_soon_threadsafe()` to inject job IDs from background threads into the queues.
    - **Guard:** Implement a 15s heartbeat to prune zombie connections.
    - **API:** `/api/events` endpoint using `EventSourceResponse`.

### 2. Optimized Notification Pipeline
- **Trigger:** Hardened hook in `run_source` after `upsert_jobs`.
- **Batching:** Introduce a 500ms "Settle Window" to prevent Telegram spam during large discovery bursts.
- **Reliability:** Ensure `deliver_queued_notifications` is called outside the `db_lock` critical section to prevent deadlocks.

### 3. Generic Adapter Framework
- **Standardization:** `v2/adapters/base.py` $\rightarrow$ `class SourceAdapter(ABC)`.
- **Interface:** `fetch()`, `normalize()`, `get_health()`.

---

## 📝 Task Breakdown

| Task | Description | Safety Guard |
|------|-------------|--------------|
| **T1.1** | Implement `ConnectionManager` with `call_soon_threadsafe` | Prevents `RuntimeError` |
| **T1.2** | Implement `/api/events` with 15s heartbeat | Prevents memory leaks |
| **T1.3** | Update `app.js` to handle SSE + heartbeat | Prevents UI hang |
| **T2.1** | Implement Notification Batching logic | Prevents Telegram spam |
| **T2.2** | Harden `run_source` $\rightarrow$ `deliver` trigger | Prevents deadlocks |
| **T3.1** | Implement `v2/adapters/base.py` | N/A |
| **T3.2** | Refactor Greenhouse to `SourceAdapter` | N/A |

---

## ✅ Verification Plan (Zero-Risk Gate)

1. **Concurrency Proof:** A standalone script must prove a `ThreadPoolExecutor` can trigger a FastAPI SSE event without crashing.
2. **Deadlock Audit:** Grep all `with db_lock` blocks to ensure no nested locking.
3. **Stress Test:** Simulate 100 new jobs in one scan $\rightarrow$ Verify Telegram sends a grouped/batched notification rather than 100 individual messages.
4. **Leak Test:** Open 10 SSE connections $\rightarrow$ Close 5 $\rightarrow$ Verify `ConnectionManager` cleaned up the queues.
