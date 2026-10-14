"""Redacted, read-only proof for the Gemini experience matcher path.

The source database is opened with SQLite read-only mode. The selected job and
cache row are copied into a disposable temporary database; only there is the
matcher gate temporarily set true in this diagnostic process to exercise the
real bridge and evaluation writer. No Gemini API calls, notification actions,
or live database writes are performed.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v2 import gemini_extractor as gemini
from v2 import radar

UTC = dt.timezone.utc
MAX_CURRENT_JOB_AGE = dt.timedelta(hours=24)
JOB_COLUMNS = (
    "id", "source", "source_job_id", "company", "title", "location", "url",
    "source_posted_at", "posted_precision", "discovered_at",
    "discovery_latency_seconds", "description", "first_seen_at", "last_seen_at",
    "canonical_opportunity_id", "canonical_match_method",
    "canonical_match_confidence",
)
CACHE_COLUMNS = (
    "input_hash", "source", "source_job_id", "title", "status", "result_json",
    "model", "created_at", "error_code",
)


def _parse_time(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _same_bound(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        return abs(float(left) - float(right)) < 1e-9
    except (TypeError, ValueError):
        return False


def _bounds_match(row: Any, low: Any, high: Any) -> bool:
    return (
        row is not None
        and _same_bound(row["experience_min_years"], low)
        and _same_bound(row["experience_max_years"], high)
    )


def _reason_count(value: Any) -> int:
    try:
        reasons = json.loads(value or "[]")
    except (TypeError, ValueError):
        return 0
    return sum(1 for reason in reasons if isinstance(reason, str)) if isinstance(reasons, list) else 0


def _has_experience_reason(value: Any) -> bool:
    try:
        reasons = json.loads(value or "[]")
    except (TypeError, ValueError):
        return False
    return isinstance(reasons, list) and any(
        isinstance(reason, str)
        and ("experience" in reason.casefold() or "year" in reason.casefold())
        for reason in reasons
    )


def _trusted_payload(payload: Any, description: str) -> dict[str, Any] | None:
    try:
        result = gemini._validate_result(
            payload, description[:gemini.MAX_DESCRIPTION_CHARS]
        )
    except (TypeError, ValueError):
        return None
    low = result.get("experience_min_years")
    high = result.get("experience_max_years")
    confidence = result.get("confidence")
    if (
        result.get("experience_type") != "required"
        or result.get("experience_scope") != "total_professional"
        or not result.get("experience_evidence")
        or not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or confidence < 0.85
        or (low is None and high is None)
    ):
        return None
    return result


def _find_candidate(
    conn: sqlite3.Connection, model: str, now: dt.datetime
) -> dict[str, Any] | None:
    conn.row_factory = sqlite3.Row
    table_names = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if not {"jobs", "gemini_shadow_cache", "job_evaluations"}.issubset(table_names):
        return None

    jobs_by_hash: dict[str, dict[str, Any]] = {}
    for row in conn.execute("SELECT * FROM jobs ORDER BY last_seen_at DESC").fetchall():
        job = dict(row)
        last_seen = _parse_time(job.get("last_seen_at"))
        if last_seen is None:
            continue
        age = now - last_seen
        if age < dt.timedelta(0) or age > MAX_CURRENT_JOB_AGE:
            continue
        jobs_by_hash[gemini._input_hash(job)] = job

    cache_rows = conn.execute(
        """SELECT input_hash, source, source_job_id, title, status, result_json,
                  model, created_at, error_code
           FROM gemini_shadow_cache
           WHERE status='ok' AND model=?
           ORDER BY created_at DESC""",
        (model,),
    ).fetchall()

    for row in cache_rows:
        input_hash = str(row["input_hash"])
        job = jobs_by_hash.get(input_hash)
        if job is None:
            continue
        cache_result = gemini._cache_lookup(conn, input_hash, model)
        if cache_result is None or cache_result[0] != "ok":
            continue
        try:
            payload = json.loads(row["result_json"] or "{}")
        except (TypeError, ValueError):
            continue
        validated = _trusted_payload(payload, str(job.get("description") or ""))
        if validated is None:
            continue
        created = _parse_time(row["created_at"])
        last_seen = _parse_time(job.get("last_seen_at"))
        if created is None or last_seen is None:
            continue
        cache_age = now - created
        job_age = now - last_seen
        if cache_age < dt.timedelta(0) or cache_age >= dt.timedelta(days=gemini.CACHE_TTL_DAYS):
            continue
        return {
            "job": job,
            "cache_row": dict(row),
            "result": validated,
            "cache_age_seconds": max(0, int(cache_age.total_seconds())),
            "job_last_seen_age_seconds": max(0, int(job_age.total_seconds())),
            "input_hash_exact_match": gemini._input_hash(job) == input_hash,
        }
    return None


def _create_sandbox_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            source_job_id TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            url TEXT NOT NULL,
            source_posted_at TEXT,
            posted_precision TEXT NOT NULL DEFAULT 'unknown',
            discovered_at TEXT NOT NULL,
            discovery_latency_seconds INTEGER,
            description TEXT NOT NULL DEFAULT '',
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            canonical_opportunity_id INTEGER,
            canonical_match_method TEXT,
            canonical_match_confidence INTEGER,
            UNIQUE(source, source_job_id)
        )
    """)
    conn.execute("""
        CREATE TABLE job_evaluations (
            job_id INTEGER PRIMARY KEY,
            evaluated_at TEXT NOT NULL,
            config_fingerprint TEXT NOT NULL,
            match INTEGER NOT NULL,
            score INTEGER NOT NULL,
            reasons_json TEXT NOT NULL,
            experience_min_years REAL,
            experience_max_years REAL,
            alertable INTEGER NOT NULL,
            alertability_reasons_json TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    """)
    gemini._ensure_cache(conn)


def _evaluate_in_sandbox(
    candidate: dict[str, Any], config: dict[str, Any], model: str
) -> dict[str, Any]:
    job = candidate["job"]
    cache_row = candidate["cache_row"]
    result = candidate["result"]

    with tempfile.TemporaryDirectory(prefix="job-radar-gemini-proof-") as directory:
        sandbox_path = Path(directory) / "probe.sqlite"
        with sqlite3.connect(sandbox_path) as conn:
            _create_sandbox_schema(conn)
            columns = ", ".join(f'"{column}"' for column in JOB_COLUMNS)
            placeholders = ", ".join("?" for _ in JOB_COLUMNS)
            conn.execute(
                f"INSERT INTO jobs ({columns}) VALUES ({placeholders})",
                tuple(job.get(column) for column in JOB_COLUMNS),
            )
            cache_columns = ", ".join(f'"{column}"' for column in CACHE_COLUMNS)
            cache_placeholders = ", ".join("?" for _ in CACHE_COLUMNS)
            conn.execute(
                f"INSERT INTO gemini_shadow_cache ({cache_columns}) "
                f"VALUES ({cache_placeholders})",
                tuple(cache_row.get(column) for column in CACHE_COLUMNS),
            )

            with patch.dict(os.environ, {
                "GEMINI_MATCHER_ENABLED": "true",
                "GEMINI_MODEL": model,
            }):
                bridged = radar._job_for_canonical(conn, int(job["id"]))
                bridge_verified = (
                    bridged is not None
                    and bridged.get("jd_experience_source") == "gemini_verified"
                )
                bridge_bounds_match = (
                    bridged is not None
                    and _same_bound(
                        bridged.get("jd_experience_min_years"),
                        result.get("experience_min_years"),
                    )
                    and _same_bound(
                        bridged.get("jd_experience_max_years"),
                        result.get("experience_max_years"),
                    )
                )
                # The real persistence function runs only against this disposable
                # one-job DB copy. The live DB remains opened read-only elsewhere.
                radar._persist_job_evaluation(conn, int(job["id"]), config)
                conn.commit()

            persisted = conn.execute(
                """SELECT experience_min_years, experience_max_years,
                          reasons_json, alertability_reasons_json
                   FROM job_evaluations WHERE job_id=?""",
                (int(job["id"]),),
            ).fetchone()
            evaluation_written = persisted is not None
            bounds_match = _bounds_match(
                persisted,
                result.get("experience_min_years"),
                result.get("experience_max_years"),
            )
            reason_present = evaluation_written and _has_experience_reason(persisted["reasons_json"])
            alert_reason_present = evaluation_written and _has_experience_reason(
                persisted["alertability_reasons_json"]
            )

            return {
                "sandbox_bridge_source_verified": bool(bridge_verified),
                "sandbox_bridge_bounds_match_cache": bool(bridge_bounds_match),
                "sandbox_evaluation_row_written": bool(evaluation_written),
                "sandbox_evaluation_min_years": (
                    persisted["experience_min_years"] if evaluation_written else None
                ),
                "sandbox_evaluation_max_years": (
                    persisted["experience_max_years"] if evaluation_written else None
                ),
                "sandbox_evaluation_bounds_match_cache": bool(bounds_match),
                "sandbox_evaluation_reason_count": (
                    _reason_count(persisted["reasons_json"]) if evaluation_written else 0
                ),
                "sandbox_evaluation_experience_reason_present": bool(reason_present),
                "sandbox_alertability_reason_count": (
                    _reason_count(persisted["alertability_reasons_json"])
                    if evaluation_written else 0
                ),
                "sandbox_alertability_experience_reason_present": bool(alert_reason_present),
            }


def diagnose_database(
    db_path: str | Path,
    config: dict[str, Any],
    *,
    model: str = "gemini-3.5-flash-lite",
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Read live DB without writes; verify one fresh exact-hash result in a sandbox."""
    db_path = Path(db_path)
    current = now or gemini._utc_now()
    current = current.astimezone(UTC) if current.tzinfo else current.replace(tzinfo=UTC)
    summary: dict[str, Any] = {
        "diagnostic_status": "not_verified",
        "model": model,
        "source_db_read_only": True,
        "source_db_modified": False,
        "gemini_api_calls_made": 0,
        "notifications_triggered": False,
    }
    if not db_path.is_file():
        summary["reason_code"] = "database_not_found"
        return summary

    uri = db_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as conn:
        conn.row_factory = sqlite3.Row
        evaluation_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(job_evaluations)")
        }
        summary["source_marker_in_job_evaluations_schema"] = (
            "jd_experience_source" in evaluation_columns
        )
        candidate = _find_candidate(conn, model, current)
        if candidate is None:
            summary["reason_code"] = "no_fresh_trusted_exact_hash_candidate"
            return summary

        job = candidate["job"]
        result = candidate["result"]
        real_eval = conn.execute(
            """SELECT experience_min_years, experience_max_years, reasons_json
               FROM job_evaluations WHERE job_id=?""",
            (int(job["id"]),),
        ).fetchone()
        sandbox = _evaluate_in_sandbox(candidate, config, model)

        summary.update({
            "diagnostic_status": "candidate_verified",
            "exact_current_input_hash_match": bool(candidate["input_hash_exact_match"]),
            "cache_status": candidate["cache_row"]["status"],
            "cache_model_matches": candidate["cache_row"]["model"] == model,
            "cache_age_seconds": candidate["cache_age_seconds"],
            "cache_ttl_days": gemini.CACHE_TTL_DAYS,
            "cache_age_within_ttl": True,
            "job_last_seen_age_seconds": candidate["job_last_seen_age_seconds"],
            "job_record_last_seen_within_24h": True,
            "experience_type": result["experience_type"],
            "experience_scope": result["experience_scope"],
            "experience_min_years": result["experience_min_years"],
            "experience_max_years": result["experience_max_years"],
            "confidence": result["confidence"],
            "verbatim_evidence_present": bool(result.get("experience_evidence")),
            "experience_range_bound_present": (
                result.get("experience_min_years") is not None
                or result.get("experience_max_years") is not None
            ),
            "live_evaluation_row_present": real_eval is not None,
            "live_evaluation_min_years": (
                real_eval["experience_min_years"] if real_eval is not None else None
            ),
            "live_evaluation_max_years": (
                real_eval["experience_max_years"] if real_eval is not None else None
            ),
            "live_evaluation_reason_count": (
                _reason_count(real_eval["reasons_json"]) if real_eval is not None else 0
            ),
            "live_evaluation_bounds_match_cache": _bounds_match(
                real_eval,
                result.get("experience_min_years"),
                result.get("experience_max_years"),
            ),
            "live_evaluation_experience_reason_present": (
                real_eval is not None and _has_experience_reason(real_eval["reasons_json"])
            ),
        })
        summary.update(sandbox)
        return summary


def _load_runtime_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError("runtime_config_not_found")
    current = json.loads(config_path.read_text(encoding="utf-8"))
    return radar.validate_config(radar._merge_config(radar._default_config(), current))


def main() -> int:
    db_path = Path(os.getenv("JOB_RADAR_DB", str(radar.DB_PATH)))
    config_path = Path(os.getenv("JOB_RADAR_RUNTIME_CONFIG", str(radar.RUNTIME_CONFIG_PATH)))
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    try:
        config = _load_runtime_config(config_path)
        summary = diagnose_database(db_path, config, model=model)
    except Exception as exc:
        print("diagnostic_status=error")
        print(f"error_type={type(exc).__name__}")
        return 2

    for key, value in summary.items():
        print(f"{key}={value}")
    return 0 if summary["diagnostic_status"] == "candidate_verified" else 3


if __name__ == "__main__":
    raise SystemExit(main())
