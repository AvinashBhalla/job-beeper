"""Persistent, disabled-by-default coordinator for paid ATS SERP discovery.

This module owns rotation, monthly spend reservation, cadence and run history.
It does not create a timer or scheduler. The coordinator refuses to make a
provider request unless an operator explicitly enables it with a positive cap.
Only DataForSEO Live is supported for recurring use because its per-request
cost is returned by the API; Serper remains available for a separately approved
benchmark, with its prepaid-credit economics handled outside this worker.
"""
from __future__ import annotations

import datetime as dt
import math
import uuid
from typing import Any, Callable

from v2 import serp_board_discovery as serp
from v2.sqlite_store import DB_LOCK, connect

UTC = dt.timezone.utc
CYCLE_INTERVAL_SECONDS = 30 * 60
LEASE_SECONDS = 5 * 60
MAX_PROVIDERS_PER_CYCLE = 2

SearchFunction = Callable[[str], dict[str, Any]]
CandidateImporter = Callable[[dict[str, Any]], dict[str, Any]]


def _utc(value: dt.datetime | None = None) -> dt.datetime:
    current = value or dt.datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _iso(value: dt.datetime | None = None) -> str:
    return _utc(value).isoformat()


def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def _row_dict(cursor: Any, row: Any) -> dict[str, Any]:
    return dict(zip([column[0] for column in cursor.description], row))


def init_schema(db_path: str) -> None:
    timestamp = _iso()
    month = _utc().strftime("%Y-%m")
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS serp_discovery_control (
                id INTEGER PRIMARY KEY CHECK(id=1),
                enabled INTEGER NOT NULL DEFAULT 0,
                monthly_cap_usd REAL,
                monthly_spend_usd REAL NOT NULL DEFAULT 0,
                budget_month TEXT NOT NULL,
                provider_cursor INTEGER NOT NULL DEFAULT 0,
                last_started_at TEXT,
                last_finished_at TEXT,
                last_outcome TEXT,
                lease_token TEXT,
                lease_until TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO serp_discovery_control(
                id,enabled,monthly_cap_usd,monthly_spend_usd,budget_month,updated_at
            ) VALUES(1,0,NULL,0,?,?)
        """, (month, timestamp))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS serp_discovery_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_token TEXT NOT NULL,
                provider TEXT NOT NULL,
                engine TEXT NOT NULL,
                query TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                outcome TEXT NOT NULL,
                organic_results INTEGER NOT NULL DEFAULT 0,
                candidate_count INTEGER NOT NULL DEFAULT 0,
                reserved_cost_usd REAL NOT NULL DEFAULT 0,
                actual_cost_usd REAL,
                error_type TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_serp_discovery_runs_started
            ON serp_discovery_runs(started_at DESC)
        """)
        conn.commit()


def configure(
    db_path: str,
    *,
    enabled: bool,
    monthly_cap_usd: float | None,
) -> dict[str, Any]:
    """Explicitly enable/disable the coordinator and set its hard monthly cap."""
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean.")
    if monthly_cap_usd is not None:
        if (
            isinstance(monthly_cap_usd, bool)
            or not isinstance(monthly_cap_usd, (int, float))
            or not math.isfinite(float(monthly_cap_usd))
        ):
            raise ValueError("monthly_cap_usd must be a finite number.")
        if monthly_cap_usd < 0:
            raise ValueError("monthly_cap_usd cannot be negative.")
    if enabled and (monthly_cap_usd is None or monthly_cap_usd <= 0):
        raise ValueError("A positive monthly spend cap is required before enabling SERP discovery.")
    init_schema(db_path)
    timestamp = _iso()
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("""
            UPDATE serp_discovery_control
            SET enabled=?,monthly_cap_usd=?,updated_at=?
            WHERE id=1
        """, (int(enabled), monthly_cap_usd, timestamp))
        conn.commit()
        cursor = conn.execute("SELECT * FROM serp_discovery_control WHERE id=1")
        return _row_dict(cursor, cursor.fetchone())


def status(db_path: str, history_limit: int = 20) -> dict[str, Any]:
    init_schema(db_path)
    with DB_LOCK, connect(db_path) as conn:
        cursor = conn.execute("SELECT * FROM serp_discovery_control WHERE id=1")
        control = _row_dict(cursor, cursor.fetchone())
        control.pop("lease_token", None)
        cursor = conn.execute("""
            SELECT provider,engine,query,started_at,finished_at,outcome,
                   organic_results,candidate_count,reserved_cost_usd,
                   actual_cost_usd,error_type
            FROM serp_discovery_runs ORDER BY id DESC LIMIT ?
        """, (max(1, min(int(history_limit), 100)),))
        runs = [_row_dict(cursor, row) for row in cursor.fetchall()]
    return {"control": control, "recent_runs": runs}


def run_once(
    db_path: str,
    *,
    searcher: SearchFunction,
    importer: CandidateImporter,
    at: dt.datetime | None = None,
    providers_per_cycle: int = MAX_PROVIDERS_PER_CYCLE,
) -> dict[str, Any]:
    """Run one explicitly enabled, budget-reserved, two-provider discovery cycle."""
    init_schema(db_path)
    current = _utc(at)
    current_text = _iso(current)
    month = current.strftime("%Y-%m")
    token = uuid.uuid4().hex

    with DB_LOCK, connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute("SELECT * FROM serp_discovery_control WHERE id=1")
        control = _row_dict(cursor, cursor.fetchone())
        if not control["enabled"]:
            conn.rollback()
            return {"outcome": "disabled", "requests_attempted": 0}
        cap = control["monthly_cap_usd"]
        if (
            cap is None
            or not isinstance(cap, (int, float))
            or not math.isfinite(float(cap))
            or float(cap) <= 0
        ):
            conn.rollback()
            return {"outcome": "budget_not_configured", "requests_attempted": 0}
        lease_until = _parse_iso(control.get("lease_until"))
        if lease_until and lease_until > current:
            conn.rollback()
            return {"outcome": "leased", "requests_attempted": 0}
        last_started = _parse_iso(control.get("last_started_at"))
        if last_started and (current - last_started).total_seconds() < CYCLE_INTERVAL_SECONDS:
            conn.rollback()
            return {"outcome": "throttled", "requests_attempted": 0}
        spend = float(control["monthly_spend_usd"] or 0)
        if control["budget_month"] != month:
            spend = 0.0
        elif not math.isfinite(spend) or spend < 0:
            conn.rollback()
            return {"outcome": "budget_invalid", "requests_attempted": 0}
        providers, next_cursor = serp.select_provider_batch(
            int(control["provider_cursor"] or 0), providers_per_cycle
        )
        conn.execute("""
            UPDATE serp_discovery_control
            SET provider_cursor=?,monthly_spend_usd=?,budget_month=?,
                last_started_at=?,last_outcome='running',
                lease_token=?,lease_until=?,updated_at=?
            WHERE id=1
        """, (
            next_cursor, spend, month, current_text, token,
            _iso(current + dt.timedelta(seconds=LEASE_SECONDS)), current_text,
        ))
        conn.commit()

    candidates: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    requests_attempted = 0
    budget_exhausted = False

    for provider in providers:
        reserve = serp.DATAFORSEO_LIVE_ESTIMATED_COST_USD
        with DB_LOCK, connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            state = conn.execute("""
                SELECT monthly_spend_usd,monthly_cap_usd,lease_token
                FROM serp_discovery_control WHERE id=1
            """).fetchone()
            if not state or state[2] != token:
                conn.rollback()
                break
            spent, monthly_cap, lease = float(state[0] or 0), float(state[1] or 0), state[2]
            if spent + reserve > monthly_cap:
                budget_exhausted = True
                conn.rollback()
                break
            conn.execute("""
                UPDATE serp_discovery_control
                SET monthly_spend_usd=monthly_spend_usd+?,updated_at=?
                WHERE id=1 AND lease_token=?
            """, (reserve, _iso(), token))
            run_cursor = conn.execute("""
                INSERT INTO serp_discovery_runs(
                    cycle_token,provider,engine,started_at,finished_at,outcome,
                    reserved_cost_usd
                ) VALUES(?,?, 'dataforseo_live',?,?, 'started',?)
            """, (token, provider, current_text, current_text, reserve))
            run_id = int(run_cursor.lastrowid)
            conn.commit()

        requests_attempted += 1
        outcome = "success"
        error_type = None
        result: dict[str, Any] = {}
        actual_cost: float | None = None
        try:
            result = searcher(provider)
            if not isinstance(result, dict):
                raise ValueError("SERP searcher must return a result dictionary.")
            raw_cost = result.get("actual_cost_usd")
            if (
                isinstance(raw_cost, (int, float))
                and not isinstance(raw_cost, bool)
                and math.isfinite(float(raw_cost))
                and raw_cost >= 0
            ):
                actual_cost = float(raw_cost)
            candidates.extend(
                item for item in result.get("candidates", [])
                if isinstance(item, dict)
            )
        except Exception as exc:
            outcome = "request_error"
            error_type = type(exc).__name__

        charged_cost = actual_cost if actual_cost is not None else reserve
        finished_text = _iso()
        with DB_LOCK, connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""
                UPDATE serp_discovery_control
                SET monthly_spend_usd=MAX(0,monthly_spend_usd+?-?),
                    updated_at=?
                WHERE id=1 AND lease_token=?
            """, (charged_cost, reserve, finished_text, token))
            conn.execute("""
                UPDATE serp_discovery_runs
                SET query=?,finished_at=?,outcome=?,organic_results=?,
                    candidate_count=?,actual_cost_usd=?,error_type=?
                WHERE id=?
            """, (
                str(result.get("query") or "")[:500], finished_text, outcome,
                max(0, int(result.get("organic_results", 0) or 0)),
                max(0, len(result.get("candidates", []))) if isinstance(result.get("candidates"), list) else 0,
                actual_cost, error_type, run_id,
            ))
            conn.commit()
        run_summaries.append({
            "provider": provider, "outcome": outcome,
            "candidate_count": max(0, len(result.get("candidates", []))) if isinstance(result.get("candidates"), list) else 0,
            "reserved_cost_usd": reserve, "actual_cost_usd": actual_cost,
            "error_type": error_type,
        })

    import_result: dict[str, Any] = {}
    import_error: str | None = None
    if candidates:
        try:
            import_result = importer({"candidates": candidates})
        except Exception as exc:
            import_error = type(exc).__name__

    finished_text = _iso()
    final_outcome = (
        "budget_exhausted" if budget_exhausted else
        "partial_failure" if any(row["outcome"] != "success" for row in run_summaries) or import_error else
        "success" if requests_attempted else "no_requests"
    )
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("""
            UPDATE serp_discovery_control
            SET last_finished_at=?,last_outcome=?,lease_token=NULL,lease_until=NULL,updated_at=?
            WHERE id=1 AND lease_token=?
        """, (finished_text, final_outcome, finished_text, token))
        conn.commit()

    return {
        "outcome": final_outcome,
        "providers": providers,
        "requests_attempted": requests_attempted,
        "candidate_count": len(candidates),
        "import_result": import_result,
        "import_error": import_error,
        "budget_exhausted": budget_exhausted,
        "runs": run_summaries,
    }
