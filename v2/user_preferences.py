"""Tenant-owned candidate preferences and per-user evaluation storage."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PREFERENCE_DEFAULTS: dict[str, Any] = {
    "target_roles": [],
    "locations": [],
    "skills": [],
    "candidate_experience_years": None,
    "min_experience_years": None,
    # Until the user configures an experience range in the UI, stay permissive.
    # A hidden three-year cap would silently exclude senior roles for new users.
    "max_experience_years": 30.0,
    "match_threshold": 55,
    "title_exclude": [],
    "excluded_role_terms": [],
    "remote_only": False,
    "max_age_hours": 72,
}

_LIST_FIELDS = {
    "target_roles", "locations", "skills", "title_exclude", "excluded_role_terms"
}
_NUMBER_FIELDS = {
    "candidate_experience_years", "min_experience_years", "max_experience_years"
}
_ALLOWED_FIELDS = set(PREFERENCE_DEFAULTS)


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_preferences(payload: dict[str, Any], require_complete: bool = True) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Preferences must be a JSON object.")
    unknown = set(payload) - _ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"Unsupported preference fields: {', '.join(sorted(unknown))}.")

    result = {**PREFERENCE_DEFAULTS, **payload}
    for field in _LIST_FIELDS:
        value = result.get(field)
        if value is None:
            value = []
        if not isinstance(value, list) or len(value) > 100:
            raise ValueError(f"{field} must be a list containing at most 100 strings.")
        normalized = []
        for item in value:
            if not isinstance(item, str) or not item.strip() or len(item.strip()) > 120:
                raise ValueError(f"{field} must contain only non-empty strings of at most 120 characters.")
            cleaned = item.strip()
            if cleaned.casefold() not in {existing.casefold() for existing in normalized}:
                normalized.append(cleaned)
        result[field] = normalized

    for field in _NUMBER_FIELDS:
        value = result.get(field)
        if value is None and field != "max_experience_years":
            continue
        if isinstance(value, bool):
            raise ValueError(f"{field} must be a number or null.")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a number or null.") from None
        if not 0 <= number <= 30:
            raise ValueError(f"{field} must be between 0 and 30.")
        result[field] = number

    if result["min_experience_years"] is not None and result["min_experience_years"] > result["max_experience_years"]:
        raise ValueError("Minimum job experience cannot exceed maximum experience.")

    threshold = result.get("match_threshold")
    if isinstance(threshold, bool):
        raise ValueError("match_threshold must be an integer between 0 and 100.")
    if isinstance(threshold, float) and not threshold.is_integer():
        raise ValueError("match_threshold must be an integer between 0 and 100.")
    try:
        threshold = int(threshold)
    except (TypeError, ValueError):
        raise ValueError("match_threshold must be an integer between 0 and 100.") from None
    if not 0 <= threshold <= 100:
        raise ValueError("match_threshold must be an integer between 0 and 100.")
    result["match_threshold"] = threshold

    max_age = result.get("max_age_hours")
    if isinstance(max_age, bool):
        raise ValueError("max_age_hours must be an integer between 1 and 720.")
    if isinstance(max_age, float) and not max_age.is_integer():
        raise ValueError("max_age_hours must be an integer between 1 and 720.")
    try:
        max_age = int(max_age)
    except (TypeError, ValueError):
        raise ValueError("max_age_hours must be an integer between 1 and 720.") from None
    if not 1 <= max_age <= 720:
        raise ValueError("max_age_hours must be an integer between 1 and 720.")
    result["max_age_hours"] = max_age

    if not isinstance(result.get("remote_only"), bool):
        raise ValueError("remote_only must be a boolean.")

    if require_complete:
        if not result["target_roles"]:
            raise ValueError("At least one target role is required before accessing the job feed.")
        if not result["locations"]:
            raise ValueError("At least one target location is required before accessing the job feed.")
    return result


def _decode_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    try:
        parsed = json.loads(row["preferences_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    preferences = {**PREFERENCE_DEFAULTS, **parsed}
    preferences["onboarding_complete"] = bool(
        preferences.get("target_roles") and preferences.get("locations")
    )
    preferences["version"] = int(row["version"])
    preferences["updated_at"] = row["updated_at"]
    return preferences


def init_preferences_schema(db_path: Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                preferences_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_job_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                preference_fingerprint TEXT NOT NULL,
                evaluated_at TEXT NOT NULL,
                match INTEGER NOT NULL,
                score INTEGER NOT NULL,
                reasons_json TEXT NOT NULL DEFAULT '[]',
                experience_min_years REAL,
                experience_max_years REAL,
                alertable INTEGER NOT NULL DEFAULT 0,
                alertability_reasons_json TEXT NOT NULL DEFAULT '[]',
                UNIQUE(user_id, job_id)
            );
            CREATE INDEX IF NOT EXISTS idx_user_job_evaluations_feed
                ON user_job_evaluations(user_id, match, evaluated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_user_job_evaluations_fingerprint
                ON user_job_evaluations(user_id, preference_fingerprint);
            """
        )


def ensure_user_preferences(db_path: Path, user_id: int) -> None:
    """Create empty defaults once, during account provisioning rather than reads."""
    timestamp = _timestamp()
    with _connect(Path(db_path)) as conn:
        conn.execute(
            """INSERT INTO user_preferences(user_id, preferences_json, version, created_at, updated_at)
               VALUES (?, '{}', 0, ?, ?) ON CONFLICT(user_id) DO NOTHING""",
            (int(user_id), timestamp, timestamp),
        )


def get_user_preferences(db_path: Path, user_id: int) -> dict[str, Any]:
    """Read preferences without acquiring a SQLite write lock."""
    with _connect(Path(db_path)) as conn:
        row = conn.execute(
            "SELECT preferences_json, version, updated_at FROM user_preferences WHERE user_id=?",
            (int(user_id),),
        ).fetchone()
    decoded = _decode_row(row)
    if decoded is None:
        raise ValueError("User preferences are not initialized for this account.")
    return decoded


def save_user_preferences(db_path: Path, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    validated = _validate_preferences(payload, require_complete=True)
    serialized = json.dumps(validated, sort_keys=True, ensure_ascii=False)
    timestamp = _timestamp()
    with _connect(Path(db_path)) as conn:
        conn.execute(
            """INSERT INTO user_preferences(user_id, preferences_json, version, created_at, updated_at)
               VALUES (?, ?, 1, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 preferences_json=excluded.preferences_json,
                 version=user_preferences.version + 1,
                 updated_at=excluded.updated_at""",
            (int(user_id), serialized, timestamp, timestamp),
        )
        row = conn.execute(
            "SELECT preferences_json, version, updated_at FROM user_preferences WHERE user_id=?",
            (int(user_id),),
        ).fetchone()
    decoded = _decode_row(row)
    if decoded is None:
        raise ValueError("User account does not exist.")
    return decoded


def migrate_first_admin_preferences(db_path: Path, global_config: dict[str, Any]) -> bool:
    """Copy the old global candidate profile to the first admin exactly once."""
    candidate = {key: global_config[key] for key in _ALLOWED_FIELDS if key in global_config}
    # Existing production config is expected to have a complete profile. If it
    # does not, preserve a safe incomplete state rather than inventing a role/location.
    normalized = _validate_preferences(candidate, require_complete=False)
    serialized = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    timestamp = _timestamp()
    with _connect(Path(db_path)) as conn:
        admin = conn.execute(
            "SELECT id FROM users WHERE role='admin' AND status='active' ORDER BY id LIMIT 1"
        ).fetchone()
        if admin is None:
            return False
        existing = conn.execute(
            "SELECT 1 FROM user_preferences WHERE user_id=?", (int(admin["id"]),)
        ).fetchone()
        if existing:
            return False
        conn.execute(
            """INSERT INTO user_preferences(user_id, preferences_json, version, created_at, updated_at)
               VALUES (?, ?, 1, ?, ?)""",
            (int(admin["id"]), serialized, timestamp, timestamp),
        )
    return True



def sync_first_admin_preferences(db_path: Path, global_config: dict[str, Any]) -> bool:
    """Keep the legacy admin config and that admin's preference row aligned."""
    candidate = {key: global_config[key] for key in _ALLOWED_FIELDS if key in global_config}
    normalized = _validate_preferences(candidate, require_complete=False)
    serialized = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    timestamp = _timestamp()
    with _connect(Path(db_path)) as conn:
        admin = conn.execute(
            "SELECT id FROM users WHERE role='admin' AND status='active' ORDER BY id LIMIT 1"
        ).fetchone()
        if admin is None:
            return False
        user_id = int(admin["id"])
        existing = conn.execute(
            "SELECT preferences_json FROM user_preferences WHERE user_id=?", (user_id,)
        ).fetchone()
        if existing is not None and existing["preferences_json"] == serialized:
            return False
        conn.execute(
            """INSERT INTO user_preferences(user_id, preferences_json, version, created_at, updated_at)
               VALUES (?, ?, 1, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 preferences_json=excluded.preferences_json,
                 version=user_preferences.version + 1,
                 updated_at=excluded.updated_at""",
            (user_id, serialized, timestamp, timestamp),
        )
    return True

def preferences_fingerprint(preferences: dict[str, Any], matcher_rules_version: int) -> str:
    payload = {
        "preferences": {key: preferences.get(key, PREFERENCE_DEFAULTS[key]) for key in sorted(_ALLOWED_FIELDS)},
        "matcher_rules_version": int(matcher_rules_version),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
