# Multi-user Authentication Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a secure admin/user identity and cookie-session foundation while keeping legacy global JobBeeper data accessible only to authenticated admins.

**Architecture:** Put password/session/rate-limit persistence in `v2/auth.py`; wire FastAPI login/current-user/logout and admin dependencies in `v2/radar.py`; add a minimal same-origin login gate to the dashboard. Keep shared job ingestion and current global matching untouched. The first admin is created out-of-band through a CLI command.

**Tech Stack:** Python 3.12, FastAPI, SQLite, `argon2-cffi`, `httpx2` for FastAPI TestClient, vanilla JavaScript/CSS, and `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-06-multi-user-auth-design.md`

## Global Constraints

- Never store plaintext passwords, session tokens, or CSRF tokens.
- Session cookies are HttpOnly, Secure by default, SameSite=Lax; only the CSRF cookie is readable by same-origin JavaScript.
- Never trust a client-supplied user ID for authorization.
- `/health` and `/api/auth/login` are public; `/api/auth/me` and `/api/auth/logout` require a session; every existing `/api/*` route is admin-only in this transitional slice.
- Do not change source collection, matching, notification delivery, production state, or global data ownership in this slice.
- Use an isolated test DB and keep Telegram disabled in tests.

## Review Focus

- Unknown email versus wrong password: both return the same response and do not disclose account existence.
- Expired, revoked, or disabled-account sessions: all protected requests reject them.
- CSRF cookie/header mismatch or missing token: every state-changing authenticated request is rejected.
- A normal `user` account: cannot read the legacy global profile, jobs with global match scores, diagnostics, or notification queue.
- Login throttling across repeated requests: limit survives process restart because counters are persisted.

---

### Task 1: Auth persistence and password/session primitives

**Files:**
- Create: `v2/auth.py`
- Create: `v2/test_auth.py`
- Modify: `v2/requirements.txt` (add `argon2-cffi>=23.1,<26`)
- Create: `v2/requirements-dev.txt` (include runtime requirements and `httpx2>=2,<3` for TestClient)

**Interfaces:**
- `init_auth_schema(db_path: Path) -> None`
- `create_user(db_path: Path, email: str, password: str, role: str = "user") -> dict[str, Any]`
- `verify_user(db_path: Path, email: str, password: str) -> dict[str, Any] | None`
- `create_session(db_path: Path, user_id: int, ttl_seconds: int = 604800) -> tuple[str, str, str]` returning raw session token, raw CSRF token, and expiry ISO timestamp.
- `get_session_user(db_path: Path, session_token: str) -> dict[str, Any] | None`
- `revoke_session(db_path: Path, session_token: str) -> bool`
- `validate_csrf(db_path: Path, session_token: str, csrf_token: str) -> bool`
- `check_login_rate_limit(db_path: Path, email: str, client_ip: str) -> bool`
- `record_login_attempt(db_path: Path, email: str, client_ip: str, success: bool) -> None`

- [ ] **Step 1: Write failing tests** for additive schema creation, normalized unique emails, Argon2id password verification, role/status validation, opaque session/CSRF token hashing, session expiry/revocation, and persistent per-email/IP login throttling (five failed attempts per 15 minutes, cleared on success).
- [ ] **Step 2: Run** `python3 -m unittest v2.test_auth -v`; expected: failures because `v2.auth` and its interfaces do not exist.
- [ ] **Step 3: Add** `argon2-cffi>=23.1,<26` to runtime requirements and create `requirements-dev.txt` with `-r requirements.txt` plus `httpx2>=2,<3`; implement only the tested persistence/password/session/rate-limit primitives. Use parameterized SQL and SHA-256 hashes for opaque tokens.
- [ ] **Step 4: Run** `python3 -m unittest v2.test_auth -v`; expected: all auth primitive tests pass.
- [ ] **Step 5: Commit** `feat(auth): add SQLite identity and session primitives`.

### Task 2: First-admin CLI, FastAPI auth endpoints, and admin-only legacy API

**Files:**
- Create: `v2/auth_admin.py`
- Modify: `v2/radar.py`
- Modify: `v2/test_auth.py`

**Interfaces:**
- `get_current_user(request: Request) -> dict[str, Any]`
- `require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]`
- `POST /api/auth/login` accepts `{ "email": string, "password": string }`, sets session and CSRF cookies, and returns the safe user record.
- `GET /api/auth/me` returns `{ "user": { "id", "email", "role", "status" } }`.
- `POST /api/auth/logout` validates CSRF, revokes the current session, and clears both cookies.
- `python3 -m v2.auth_admin create-admin --email <email>` prompts for password twice and creates the first admin only.
- `python3 -m v2.auth_admin create-user --email <email>` prompts for a password and provisions a `user` account for invite-only beta access.

- [ ] **Step 1: Write failing API tests** for login success, generic bad-credential response, 429 throttling, current-user response, logout/replay rejection, CSRF validation, CLI refusing a second bootstrap admin, CLI user provisioning, and role access.
- [ ] **Step 2: Run** `python3 -m unittest v2.test_auth -v`; expected: new API/CLI tests fail before implementation.
- [ ] **Step 3: Implement** FastAPI dependencies and auth endpoints; initialize additive auth tables during existing DB initialization; add admin CLI commands for one-time admin bootstrap and ordinary user provisioning. Apply `Depends(require_admin)` to every existing `/api/*` route except the explicit auth routes. Do not alter `/health`.
- [ ] **Step 4: Run** `python3 -m unittest v2.test_auth -v`; expected: API, CSRF, throttle, and role tests pass.
- [ ] **Step 5: Commit** `feat(auth): add login sessions and admin route guards`.

### Task 3: Dashboard login and session lifecycle

**Files:**
- Create: `dashboard/auth.js` (small, independently testable cookie-session client)
- Modify: `dashboard/index.html`
- Modify: `dashboard/app.js`
- Modify: `dashboard/styles.css`
- Create: `v2/test_dashboard_auth_contract.py`

**Interfaces:**
- Dashboard calls same-origin `/api/auth/login`, `/api/auth/me`, and `/api/auth/logout` with `credentials: "same-origin"`.
- Store no session token in localStorage or sessionStorage. Read the CSRF cookie and send it as `X-CSRF-Token` for logout and other state-changing authenticated requests.
- Existing global dashboard screens render only after `/api/auth/me` confirms role `admin`; `user` role sees a clear beta-not-enabled state rather than any global data.

- [ ] **Step 1: Add failing tests** in `v2/test_dashboard_auth_contract.py` that exercise the actual `dashboard/auth.js` client under Node (login, `/api/auth/me`, same-origin credentials, CSRF header on writes/logout, and admin-vs-user bootstrap callbacks) and validate the shipped login/holding markup and script order.
- [ ] **Step 2: Run** `python3 -m unittest v2.test_dashboard_auth_contract -v`; expected: failures against the current config-token-only dashboard. The Node contract test skips only when Node.js is unavailable; run it separately on a Node-enabled host/CI runner.
- [ ] **Step 3: Implement** a minimal login form, logout control, session bootstrap, CSRF header helper, and user-role holding screen. Remove the browser's `X-Config-Token` flow and `sessionStorage` token key. Preserve theme and applied-job localStorage keys; do not confuse them with auth.
- [ ] **Step 4: Run** `python3 -m unittest v2.test_dashboard_auth_contract v2.test_auth -v`; expected: both contract and API suites pass.
- [ ] **Step 5: Commit** `feat(dashboard): use cookie sessions for admin access`.

### Task 4: Full regression, docs, and review readiness

**Files:**
- Modify: `docs/MULTI_USER_AND_REFERRAL_ROADMAP.md`
- Modify: `docs/JOB_RADAR_HANDOVER.md`
- Modify: `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`
- Modify: `docs/superpowers/specs/2026-11-06-multi-user-auth-design.md`
- Modify: `docs/superpowers/plans/2026-11-06-multi-user-auth-foundation.md`

- [ ] **Step 1: Add/adjust route-matrix tests** that enumerate every existing `/api/*` route, assert anonymous and `user` sessions are denied, assert an `admin` session reaches the handler, and assert `/health` plus login remain public.
- [ ] **Step 2: Run** `python3 -m unittest v2.test_auth -v`; expected: the route-matrix tests fail for any missing guard and pass once all guards are applied.
- [ ] **Step 3: Correct** missing guards and update handover docs with actual implemented scope, bootstrap command, environment requirements, and explicit next milestone (user preferences/evaluations).
- [ ] **Step 4: Run** the full V2 suite with `python3 -m unittest discover -s v2 -p 'test_*.py' -v`; expected: all tests pass, no live network calls, no Telegram sends.
- [ ] **Step 5: Commit** `docs(auth): document multi-user foundation and rollout gates`.

## Completion gates

- Every new behavior has a test observed failing before implementation and passing afterward.
- Full V2 suite passes in a throwaway/test environment.
- No production container, database, config, volume, scheduler, or notifications changed.
- A fresh whole-branch review is completed; any Critical/Important finding is fixed with TDD before PR creation.
- PR targets `v2-live-radar`, never `main`; deployment remains a separate explicit authorization.
