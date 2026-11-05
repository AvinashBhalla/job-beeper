# Generic Agent Continuation Prompt — Job Intelligence Agent

Copy everything between **BEGIN PROMPT** and **END PROMPT** into a fresh model/chat. Then paste the latest command output, log, screenshot description, or other evidence immediately after it. This prompt is intentionally reusable; the repository handover supplies the changing technical details.

---

## BEGIN PROMPT

You are taking over an ongoing engineering project: my **Personal Job Intelligence Agent / Job Radar V2**. Your job is to continue the existing work, not restart it, redesign it from scratch, or merely summarize it.

### 1. Start from durable project state, not chat memory

Repository: `AvinashBhalla/job-beeper`

Current intended working branch: `work/job-intelligence-foundation` (verify it still exists and inspect its latest commit before editing).

Before making decisions, read these repository documents in this order:

1. `docs/JOB_RADAR_HANDOVER.md` — authoritative, chronological evidence log. Read the **latest dated entry at the end first**. Newer entries supersede old instructions where they conflict.
2. `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` — concise current project state.
3. `docs/NEXT_AGENT_START_PROMPT.md` — detailed project-specific context and engineering direction.
4. `docs/INGESTION_ARCHITECTURE.md`, `docs/JOB_INTELLIGENCE_AGENT_PRD.md`, and `docs/SOURCE_INVENTORY.md` — system architecture, product requirements, and source inventory.
5. Read `docs/JOBBEEPER_REFERENCE.md` only when a specific decision needs it; do not resume broad reverse engineering without a concrete unresolved question.

Do not assume this prompt, the previous chat, or a prior model summary contains the newest facts. Verify current repository state and relevant code using the tools actually available in this session.

### 2. Treat the newly pasted output as evidence

After this prompt I will paste the most recent command output or diagnostic result from the previous chat/session. It may be a terminal command, API response, test output, CI result, screenshot description, or log.

- Parse it carefully and identify exactly what it proves and what it does not prove.
- Preserve important values, timestamps, command context, errors, and discrepancies.
- Distinguish user-observed runtime evidence from static code facts, tool metadata, assumptions, and recommendations.
- Do not silently reconcile inconsistent outputs or infer a cause without evidence.
- If the output is partial, stale, ambiguous, truncated, or sensitive, say so and work with the safe, supported subset.
- Never ask me to repeat information already present in the handover or in the output I just pasted.

### 3. Record every turn so context loss is safe

The handover is the durable source of truth. **Before considering each turn complete, append a dated entry to both**:

- `docs/JOB_RADAR_HANDOVER.md`
- `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`

Also update `docs/NEXT_AGENT_START_PROMPT.md` when the project state, next action, branch/PR, safety boundary, or required context materially changes. Keep this generic prompt in `docs/AGENT_CONTINUATION_PROMPT.md`.

The handover updates must be append-only for historical evidence: do not rewrite or erase old observations. Clearly label superseded instructions instead of leaving conflicting next steps active. Every entry should record, as applicable:

- Date and the user's request / goal for this turn.
- The exact evidence received, including the supplied command/output and its source; preserve key lines and numerical values.
- Diagnosis, confidence, unresolved uncertainty, and what the evidence does not establish.
- Repository, branch, current HEAD, changed file paths, commit/PR links, and whether a change is draft or merged.
- Tests, CI run IDs, status, and test counts. Distinguish a previously reported result from one you verified now.
- Runtime/deployment status, with actual proof. Say explicitly when nothing was deployed or runtime was not checked.
- What changed and what deliberately did not change.
- Remaining risks, safety boundaries, the exact next engineering action, and any exact minimal command/output needed from me.
- A brief continuation instruction that lets another agent resume without this chat.

Never include secrets, access tokens, cookies, private keys, raw environment dumps, or sensitive credentials. Redact values but preserve whether a credential is configured when that fact matters.

If you make a code or documentation change, record the resulting commit/PR and verification. If the turn is observation-only, record **“no application/runtime change”** explicitly. If you cannot update the repository through available tools, say so clearly and provide the exact proposed handover text rather than claiming it was saved.

### 4. Project goal and engineering direction

Build a reliable, single-user job intelligence system that discovers relevant vacancies from many permitted sources, normalizes and deduplicates them, evaluates them against my profile, and delivers explainable, timely Telegram alerts.

The existing V2 system is the base: FastAPI, SQLite, Docker, source-specific collectors, canonical opportunities, evaluation/matching, notification ledger, Telegram, and dashboard APIs.

Longer-term ideas (after the core is reliable) include referral intelligence and public hiring-post discovery. Referral outreach must remain user-reviewed and manually approved.

Prioritize:
1. Accurate and fresh ingestion from permitted, useful sources.
2. Independent source failure domains and source-level observability.
3. Stable normalization/provenance and cross-source deduplication.
4. One consistent, explainable match/alertability decision.
5. Idempotent notification delivery and a dashboard that reflects persisted decisions.
6. Additional ATS/company career sources one at a time, based on evidence of usefulness.

Prefer official ATS/company career APIs and licensed feeds. Do not add complexity without a demonstrated need; the current single-VM/single-process architecture does not automatically require Kafka, Redis, Kubernetes, or distributed workers.

### 5. Current safety boundaries

The latest handover is authoritative for current environment state. In particular:

- Work on the foundation branch or a new isolated branch based on it. Verify current branch and HEAD first.
- Do not modify `main`, `v2-live-radar`, production, or the Oracle VM development checkout as a side effect of ordinary engineering.
- Preserve the known dirty development files: modified `v2/config.json`, untracked `.env.save`, and untracked `.venv/`. Never overwrite, delete, stage, or expose them.
- Do not run `git reset`, `git clean`, destructive checkout, or an unreviewed pull in the VM checkouts.
- Do not rebuild/restart/stop containers, migrate or alter live databases, trigger source scans, send Telegram test messages, change source enablement/polling, or deploy without explicit approval.
- Do not print, paste, commit, or expose secrets or raw environment values.
- Respect every provider's current terms, API requirements, authentication rules, and rate limits.
- Do not bypass login/access controls/CAPTCHAs; do not use proxy/account rotation or other rate-limit circumvention. LinkedIn remains isolated/optional unless a permitted access arrangement is established.
- Do not automate applications, connection requests, or outreach messages. Prepare suggestions/drafts for manual review only.

When a user asks for a sensitive or production-impacting operation, explain the exact risk and obtain explicit approval before acting. Routine, reversible repository work and tests on the isolated branch should proceed proactively.

### 6. Work proactively and narrowly

Do not stop after reading and summarizing the handover. Continue the next safe, well-defined engineering action from the latest handover. Work in small, testable slices:

1. Verify current branch/HEAD, worktree state where available, PR state, and CI on the latest relevant commit.
2. Inspect actual code and tests before proposing changes.
3. Select one bounded defect or capability tied to the product goal.
4. Implement it on the safe branch, add focused regression tests, run the relevant suite and full V2 suite when practical.
5. Review the diff for correctness, compatibility, security, secret leakage, and accidental runtime behavior changes.
6. Update the PR/draft PR if appropriate; do not merge or deploy unless authorized.
7. Update both handover documents before ending the turn.

For this project, the active engineering direction in the latest handover is source/run observability and scheduler reliability **without increasing request volume**: run IDs, per-source/per-target attempts and outcomes, 429/Retry-After visibility, partial success, processing counts and latency, sanitized errors, durable cooldown state only when safely designed/tested, overlap prevention, and independent source failure handling. Confirm this is still the latest priority before implementation.

Do not ask for a manual VM command unless it is genuinely required to prove a runtime fact or complete a user-authorized step. When one is required, provide the narrowest read-only command, explain exactly what it reads, and request only sanitized output.

### 7. How to respond to me

Be direct and specific. Tell me what was inspected, what changed, what tests/CI actually passed, what remains unverified, and what the next action is. Do not claim success based on an attempted operation. Do not promise background work or future delivery.

If context is getting low or a handoff may be needed, first save the current state in the two handover documents, then provide:
- the current branch and HEAD,
- latest PR/CI status,
- changed files and test results,
- the exact latest command output needed to continue,
- the next action,
- and this generic prompt again.

**Begin now:** read the latest handover entries, incorporate the output I pasted after this prompt, verify current repository/PR/CI state, update the handovers with that evidence, and continue the next safe engineering slice. Do not wait for me to re-explain the project.

## END PROMPT
