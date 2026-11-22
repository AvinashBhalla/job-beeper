"""Creator-only, label-scoped Gmail integration for Google Alerts.

This module contains the OAuth/token boundary, a Gmail REST client that enforces
label scope, and durable sync/notification-event staging. It deliberately does
not fetch arbitrary job URLs or write Gmail message bodies to SQLite.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode, urlsplit, quote

import requests
from cryptography.fernet import Fernet, InvalidToken

from v2.google_alerts_email import (
    GoogleAlertEmailError,
    is_google_alerts_metadata,
    parse_google_alert_email,
)
from v2.sqlite_store import DB_LOCK, connect as connect_sqlite


GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
GMAIL_API_ROOT = "https://gmail.googleapis.com/gmail/v1"
GOOGLE_ALERTS_LABEL_NAME = "JobBeeper/GoogleAlerts"
CALLBACK_PATH = "/api/integrations/google-alerts/gmail/callback"
STATE_TTL_SECONDS = 600
MAX_GMAIL_PAGE_SIZE = 500
MAX_PUSH_BODY_BYTES = 64 * 1024
MAX_MESSAGE_ATTEMPTS = 6

# Access tokens are short-lived and intentionally kept only in process memory.
# The owner-only worker reuses a token until a small expiry safety window.
_ACCESS_TOKEN_CACHE: dict[tuple[str, int], tuple[str, float]] = {}
_ACCESS_TOKEN_CACHE_LOCK = threading.RLock()


class GoogleAlertsGmailError(RuntimeError):
    """Sanitized integration error. Never include tokens, bodies or API payloads."""

    def __init__(self, code: str, *, retryable: bool = False, status_code: int | None = None):
        self.code = code
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(code)


@dataclass(frozen=True)
class GmailIntegrationConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    owner_user_id: int
    owner_email: str
    token_encryption_key: str
    pubsub_topic: str | None = None
    pubsub_subscription: str | None = None
    push_audience: str | None = None
    push_service_account_email: str | None = None
    live_access_enabled: bool = False
    sync_mode: str = "polling"
    poll_interval_seconds: int = 180


def load_config(environ: dict[str, str] | None = None) -> GmailIntegrationConfig | None:
    """Load owner-only Gmail config; polling needs no public webhook resources."""
    values = os.environ if environ is None else environ
    names = {
        "client_id": "JOB_RADAR_GMAIL_OAUTH_CLIENT_ID",
        "client_secret": "JOB_RADAR_GMAIL_OAUTH_CLIENT_SECRET",
        "redirect_uri": "JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI",
        "owner_user_id": "JOB_RADAR_GMAIL_OWNER_USER_ID",
        "owner_email": "JOB_RADAR_GMAIL_OWNER_EMAIL",
        "token_encryption_key": "JOB_RADAR_GMAIL_TOKEN_ENCRYPTION_KEY",
        "pubsub_topic": "JOB_RADAR_GMAIL_PUBSUB_TOPIC",
        "pubsub_subscription": "JOB_RADAR_GMAIL_PUBSUB_SUBSCRIPTION",
        "push_audience": "JOB_RADAR_GMAIL_PUSH_AUDIENCE",
        "push_service_account_email": "JOB_RADAR_GMAIL_PUSH_SERVICE_ACCOUNT_EMAIL",
    }
    raw = {key: str(values.get(env_name, "")).strip() for key, env_name in names.items()}
    if not any(raw.values()):
        return None
    required = ("client_id", "client_secret", "redirect_uri", "owner_user_id", "owner_email", "token_encryption_key")
    if any(not raw[key] for key in required):
        raise GoogleAlertsGmailError("gmail_integration_configuration_incomplete")
    try:
        owner_user_id = int(raw["owner_user_id"])
    except (TypeError, ValueError):
        raise GoogleAlertsGmailError("gmail_owner_user_id_invalid") from None
    if owner_user_id <= 0:
        raise GoogleAlertsGmailError("gmail_owner_user_id_invalid")

    redirect = urlsplit(raw["redirect_uri"])
    try:
        redirect_port = redirect.port
    except ValueError:
        raise GoogleAlertsGmailError("gmail_redirect_uri_invalid") from None
    hostname = (redirect.hostname or "").casefold()
    local_callback = hostname == "localhost"
    if (
        not hostname or redirect.username or redirect.password or redirect.query
        or redirect.fragment or redirect.path != CALLBACK_PATH
        or (local_callback and redirect.scheme.lower() not in {"http", "https"})
        or (not local_callback and redirect.scheme.lower() != "https")
    ):
        raise GoogleAlertsGmailError("gmail_redirect_uri_invalid")
    if not local_callback:
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            raise GoogleAlertsGmailError("gmail_redirect_uri_invalid")
    if redirect_port is not None and not 1 <= redirect_port <= 65535:
        raise GoogleAlertsGmailError("gmail_redirect_uri_invalid")
    if "@" not in raw["owner_email"] or len(raw["owner_email"]) > 254:
        raise GoogleAlertsGmailError("gmail_owner_email_invalid")
    _fernet(raw["token_encryption_key"])

    sync_mode = str(values.get("JOB_RADAR_GMAIL_SYNC_MODE", "polling")).strip().lower() or "polling"
    if sync_mode not in {"polling", "push"}:
        raise GoogleAlertsGmailError("gmail_sync_mode_invalid")
    push_keys = ("pubsub_topic", "pubsub_subscription", "push_audience", "push_service_account_email")
    supplied_push = [bool(raw[key]) for key in push_keys]
    if any(supplied_push) and not all(supplied_push):
        raise GoogleAlertsGmailError("gmail_pubsub_configuration_incomplete")
    if sync_mode == "push" and not all(supplied_push):
        raise GoogleAlertsGmailError("gmail_pubsub_configuration_incomplete")
    try:
        poll_interval = int(values.get("JOB_RADAR_GMAIL_POLL_INTERVAL_SECONDS", "180"))
    except (TypeError, ValueError):
        raise GoogleAlertsGmailError("gmail_poll_interval_invalid") from None
    if not 60 <= poll_interval <= 3600:
        raise GoogleAlertsGmailError("gmail_poll_interval_invalid")

    return GmailIntegrationConfig(
        client_id=raw["client_id"], client_secret=raw["client_secret"],
        redirect_uri=raw["redirect_uri"], owner_user_id=owner_user_id,
        owner_email=raw["owner_email"].casefold(),
        token_encryption_key=raw["token_encryption_key"],
        pubsub_topic=raw["pubsub_topic"] or None,
        pubsub_subscription=raw["pubsub_subscription"] or None,
        push_audience=raw["push_audience"] or None,
        push_service_account_email=raw["push_service_account_email"].casefold() or None,
        live_access_enabled=str(values.get("JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS", "")).strip().lower() in {"1", "true", "yes", "on"},
        sync_mode=sync_mode, poll_interval_seconds=poll_interval,
    )


def _fernet(key: str) -> Fernet:
    try:
        return Fernet(key.encode("ascii"))
    except Exception:
        raise GoogleAlertsGmailError("gmail_token_encryption_key_invalid") from None


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = connect_sqlite(Path(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _valid_gmail_id(value: object) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 256:
        return None
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in value):
        return None
    return value


def init_schema(db_path: str | Path) -> None:
    """Create only integration-owned tables; no mailbox operation happens here."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with DB_LOCK, _connect(path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS google_alerts_gmail_oauth_states (
            state_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code_verifier TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_google_alerts_oauth_expiry
          ON google_alerts_gmail_oauth_states(expires_at);

        CREATE TABLE IF NOT EXISTS google_alerts_gmail_credentials (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            account_email_hash TEXT NOT NULL,
            encrypted_refresh_token BLOB NOT NULL,
            scopes TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS google_alerts_gmail_sync_state (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            label_id TEXT NOT NULL,
            history_id TEXT,
            initial_history_id TEXT,
            backfill_page_token TEXT,
            backfill_state TEXT NOT NULL DEFAULT 'not_started',
            watch_expiration_ms INTEGER,
            last_reconciled_at TEXT,
            history_page_token TEXT,
            history_start_id TEXT,
            history_candidate_id TEXT,
            last_error_code TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS google_alerts_gmail_messages (
            message_id_hash TEXT PRIMARY KEY,
            gmail_message_id TEXT,
            internal_date_ms INTEGER,
            history_backfill INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'queued',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT,
            result_count INTEGER NOT NULL DEFAULT 0,
            error_code TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            processed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_google_alerts_gmail_messages_due
          ON google_alerts_gmail_messages(status, next_attempt_at, created_at);

        CREATE TABLE IF NOT EXISTS google_alerts_gmail_push_events (
            pubsub_message_id TEXT PRIMARY KEY,
            history_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            processed_at TEXT,
            error_code TEXT
        );

        CREATE TABLE IF NOT EXISTS google_alerts_gmail_opportunities (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            canonical_opportunity_id INTEGER NOT NULL REFERENCES canonical_opportunities(id) ON DELETE CASCADE,
            candidate_job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            history_backfill INTEGER NOT NULL DEFAULT 0,
            first_observed_at TEXT NOT NULL,
            last_observed_at TEXT NOT NULL,
            PRIMARY KEY(user_id, canonical_opportunity_id)
        );
        CREATE INDEX IF NOT EXISTS idx_google_alerts_gmail_opportunities_job
          ON google_alerts_gmail_opportunities(user_id, candidate_job_id);
        """)
        columns = {
            row[1] for row in conn.execute(
                "PRAGMA table_info(google_alerts_gmail_sync_state)"
            )
        }
        for column in ("history_page_token", "history_start_id", "history_candidate_id"):
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE google_alerts_gmail_sync_state ADD COLUMN {column} TEXT"
                )


def create_authorization_url(
    db_path: str | Path,
    user_id: int,
    config: GmailIntegrationConfig,
    *,
    now_seconds: int | None = None,
) -> str:
    """Create a one-time state + PKCE challenge for the creator-only OAuth grant."""
    if int(user_id) != config.owner_user_id:
        raise GoogleAlertsGmailError("gmail_owner_only")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    timestamp = int(time.time() if now_seconds is None else now_seconds)
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "DELETE FROM google_alerts_gmail_oauth_states WHERE expires_at<=?",
            (timestamp,),
        )
        conn.execute(
            """INSERT INTO google_alerts_gmail_oauth_states
               (state_hash,user_id,code_verifier,created_at,expires_at)
               VALUES(?,?,?,?,?)""",
            (_hash(state), int(user_id), verifier, _now_iso(), timestamp + STATE_TTL_SECONDS),
        )
    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "false",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


def consume_authorization_state(
    db_path: str | Path,
    state: str,
    *,
    now_seconds: int | None = None,
) -> tuple[int, str] | None:
    if not isinstance(state, str) or not state or len(state) > 512:
        return None
    timestamp = int(time.time() if now_seconds is None else now_seconds)
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """SELECT user_id,code_verifier
               FROM google_alerts_gmail_oauth_states
               WHERE state_hash=? AND expires_at>?""",
            (_hash(state), timestamp),
        ).fetchone()
        conn.execute(
            "DELETE FROM google_alerts_gmail_oauth_states WHERE state_hash=?",
            (_hash(state),),
        )
        conn.execute(
            "DELETE FROM google_alerts_gmail_oauth_states WHERE expires_at<=?",
            (timestamp,),
        )
    if row is None:
        return None
    return int(row["user_id"]), str(row["code_verifier"])


def _extract_scopes(payload: dict[str, Any]) -> set[str]:
    raw = payload.get("scope", "")
    if not isinstance(raw, str):
        return set()
    return {scope for scope in raw.split() if scope}


def _require_readonly_scope(payload: dict[str, Any]) -> None:
    scopes = _extract_scopes(payload)
    if GMAIL_SCOPE not in scopes or scopes - {GMAIL_SCOPE}:
        raise GoogleAlertsGmailError("gmail_scope_mismatch")


def exchange_authorization_code(
    code: str,
    verifier: str,
    config: GmailIntegrationConfig,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    if not isinstance(code, str) or not code or len(code) > 4096:
        raise GoogleAlertsGmailError("gmail_authorization_code_invalid")
    client = session or requests
    try:
        response = client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uri": config.redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
            timeout=(5, 20),
        )
    except requests.RequestException:
        raise GoogleAlertsGmailError("gmail_token_exchange_network_error", retryable=True) from None
    if response.status_code != 200:
        raise GoogleAlertsGmailError(
            "gmail_token_exchange_rejected",
            retryable=response.status_code >= 500,
            status_code=response.status_code,
        )
    try:
        payload = response.json()
    except (ValueError, AttributeError):
        raise GoogleAlertsGmailError("gmail_token_exchange_invalid_response") from None
    if not isinstance(payload, dict):
        raise GoogleAlertsGmailError("gmail_token_exchange_invalid_response")
    _require_readonly_scope(payload)
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleAlertsGmailError("gmail_access_token_missing")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise GoogleAlertsGmailError("gmail_refresh_token_missing")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": max(0, int(payload.get("expires_in") or 0)),
        "scopes": " ".join(sorted(_extract_scopes(payload))),
    }


def save_credentials(
    db_path: str | Path,
    user_id: int,
    account_email: str,
    refresh_token: str,
    scopes: str,
    config: GmailIntegrationConfig,
) -> None:
    if int(user_id) != config.owner_user_id:
        raise GoogleAlertsGmailError("gmail_owner_only")
    normalized_email = str(account_email or "").strip().casefold()
    if not normalized_email or normalized_email != config.owner_email:
        raise GoogleAlertsGmailError("gmail_account_not_owner")
    scope_set = {scope for scope in str(scopes or "").split() if scope}
    if scope_set != {GMAIL_SCOPE}:
        raise GoogleAlertsGmailError("gmail_scope_mismatch")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise GoogleAlertsGmailError("gmail_refresh_token_missing")
    encrypted = _fernet(config.token_encryption_key).encrypt(refresh_token.encode("utf-8"))
    stamp = _now_iso()
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO google_alerts_gmail_credentials(
                 singleton,owner_user_id,account_email_hash,encrypted_refresh_token,
                 scopes,created_at,updated_at
               ) VALUES(1,?,?,?,?,?,?)
               ON CONFLICT(singleton) DO UPDATE SET
                 owner_user_id=excluded.owner_user_id,
                 account_email_hash=excluded.account_email_hash,
                 encrypted_refresh_token=excluded.encrypted_refresh_token,
                 scopes=excluded.scopes,
                 updated_at=excluded.updated_at""",
            (
                int(user_id), _hash(normalized_email), encrypted, GMAIL_SCOPE,
                stamp, stamp,
            ),
        )
    clear_access_token_cache(db_path, user_id)


def load_refresh_token(
    db_path: str | Path,
    user_id: int,
    config: GmailIntegrationConfig,
) -> str:
    with _connect(db_path) as conn:
        row = conn.execute(
            """SELECT owner_user_id,account_email_hash,encrypted_refresh_token,scopes
               FROM google_alerts_gmail_credentials WHERE singleton=1"""
        ).fetchone()
    if row is None:
        raise GoogleAlertsGmailError("gmail_not_connected")
    if int(row["owner_user_id"]) != int(user_id) or int(user_id) != config.owner_user_id:
        raise GoogleAlertsGmailError("gmail_owner_only")
    if row["account_email_hash"] != _hash(config.owner_email):
        raise GoogleAlertsGmailError("gmail_account_binding_mismatch")
    if str(row["scopes"] or "") != GMAIL_SCOPE:
        raise GoogleAlertsGmailError("gmail_scope_mismatch")
    try:
        return _fernet(config.token_encryption_key).decrypt(
            bytes(row["encrypted_refresh_token"])
        ).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, TypeError):
        raise GoogleAlertsGmailError("gmail_refresh_token_decryption_failed") from None


def clear_access_token_cache(
    db_path: str | Path | None = None,
    user_id: int | None = None,
) -> None:
    """Forget volatile OAuth access tokens, optionally for one local account."""
    path_key = str(Path(db_path).resolve()) if db_path is not None else None
    with _ACCESS_TOKEN_CACHE_LOCK:
        for key in list(_ACCESS_TOKEN_CACHE):
            if path_key is not None and key[0] != path_key:
                continue
            if user_id is not None and key[1] != int(user_id):
                continue
            _ACCESS_TOKEN_CACHE.pop(key, None)


def refresh_access_token(
    db_path: str | Path,
    config: GmailIntegrationConfig,
    *,
    session: requests.Session | None = None,
    now_seconds: float | None = None,
    force_refresh: bool = False,
) -> str:
    """Return a cached in-memory Gmail access token or refresh it safely.

    The refresh token remains encrypted in SQLite. Access tokens are never
    persisted and are invalidated whenever the owner replaces/disconnects the
    Gmail grant. The expiry margin prevents a worker cycle from using a token
    that is about to expire during a multi-request sync operation.
    """
    cache_key = (str(Path(db_path).resolve()), int(config.owner_user_id))
    timestamp = float(time.time() if now_seconds is None else now_seconds)
    if not force_refresh:
        with _ACCESS_TOKEN_CACHE_LOCK:
            cached = _ACCESS_TOKEN_CACHE.get(cache_key)
            if cached and cached[1] > timestamp:
                return cached[0]

    refresh_token = load_refresh_token(db_path, config.owner_user_id, config)
    client = session or requests
    try:
        response = client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=(5, 20),
        )
    except requests.RequestException:
        raise GoogleAlertsGmailError("gmail_token_refresh_network_error", retryable=True) from None
    if response.status_code != 200:
        raise GoogleAlertsGmailError(
            "gmail_token_refresh_rejected",
            retryable=response.status_code >= 500,
            status_code=response.status_code,
        )
    try:
        payload = response.json()
    except (ValueError, AttributeError):
        raise GoogleAlertsGmailError("gmail_token_refresh_invalid_response") from None
    if not isinstance(payload, dict):
        raise GoogleAlertsGmailError("gmail_token_refresh_invalid_response")
    # Refresh responses may omit scope; when present it must remain read-only.
    if payload.get("scope"):
        _require_readonly_scope(payload)
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleAlertsGmailError("gmail_access_token_missing")
    try:
        expires_in = float(payload.get("expires_in", 3600))
    except (TypeError, ValueError):
        raise GoogleAlertsGmailError("gmail_token_expiry_invalid") from None
    if not 0 < expires_in <= 86400:
        raise GoogleAlertsGmailError("gmail_token_expiry_invalid")
    safety_margin = min(60.0, max(5.0, expires_in * 0.1))
    usable_until = timestamp + max(1.0, expires_in - safety_margin)
    with _ACCESS_TOKEN_CACHE_LOCK:
        _ACCESS_TOKEN_CACHE[cache_key] = (access_token, usable_until)
    return access_token


class GmailApiClient:
    """Small REST client; all mailbox discovery methods require the exact label ID."""

    def __init__(
        self,
        access_token: str,
        *,
        session: requests.Session | None = None,
        timeout: tuple[int, int] = (5, 20),
        refresh_access_token: Callable[[], str] | None = None,
    ):
        if not isinstance(access_token, str) or not access_token:
            raise GoogleAlertsGmailError("gmail_access_token_missing")
        self.access_token = access_token
        self.session = session or requests.Session()
        self.timeout = timeout
        self.refresh_access_token = refresh_access_token

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: list[tuple[str, object]] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{GMAIL_API_ROOT}/{path.lstrip('/')}"
        for attempt in range(2):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    params=params,
                    json=json_body,
                    timeout=self.timeout,
                )
            except requests.RequestException:
                raise GoogleAlertsGmailError("gmail_api_network_error", retryable=True) from None
            if response.status_code != 401 or attempt == 1 or self.refresh_access_token is None:
                break
            # Google can invalidate an access token before its advertised expiry.
            # Refresh once and retry the exact request; never loop on persistent 401s.
            refreshed = self.refresh_access_token()
            if not isinstance(refreshed, str) or not refreshed:
                raise GoogleAlertsGmailError("gmail_access_token_refresh_failed")
            self.access_token = refreshed
        if response.status_code in {429, 500, 502, 503, 504}:
            raise GoogleAlertsGmailError(
                "gmail_api_temporary_failure",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise GoogleAlertsGmailError(
                "gmail_api_request_rejected",
                retryable=False,
                status_code=response.status_code,
            )
        try:
            payload = response.json()
        except (ValueError, AttributeError):
            raise GoogleAlertsGmailError("gmail_api_invalid_response") from None
        if not isinstance(payload, dict):
            raise GoogleAlertsGmailError("gmail_api_invalid_response")
        return payload

    def get_profile(self) -> dict[str, Any]:
        payload = self._request("GET", "users/me/profile")
        email = payload.get("emailAddress")
        history_id = payload.get("historyId")
        if not isinstance(email, str) or not email or not isinstance(history_id, str) or not history_id.isdigit():
            raise GoogleAlertsGmailError("gmail_profile_invalid")
        return {"email_address": email.casefold(), "history_id": history_id}

    def resolve_alert_label_id(self) -> str:
        payload = self._request("GET", "users/me/labels")
        labels = payload.get("labels", [])
        matches = [
            item for item in labels
            if isinstance(item, dict)
            and item.get("name") == GOOGLE_ALERTS_LABEL_NAME
            and item.get("type") == "user"
            and isinstance(item.get("id"), str)
        ]
        if len(matches) != 1:
            raise GoogleAlertsGmailError(
                "gmail_label_missing" if not matches else "gmail_label_ambiguous"
            )
        return str(matches[0]["id"])

    def watch(self, label_id: str, topic_name: str) -> dict[str, Any]:
        _require_label_id(label_id)
        if not isinstance(topic_name, str) or not topic_name.startswith("projects/"):
            raise GoogleAlertsGmailError("gmail_pubsub_topic_invalid")
        payload = self._request(
            "POST",
            "users/me/watch",
            json_body={
                "topicName": topic_name,
                "labelIds": [label_id],
                "labelFilterBehavior": "INCLUDE",
            },
        )
        history_id = payload.get("historyId")
        expiration = payload.get("expiration")
        if not isinstance(history_id, str) or not history_id.isdigit():
            raise GoogleAlertsGmailError("gmail_watch_response_invalid")
        try:
            expiration_ms = int(expiration)
        except (TypeError, ValueError):
            expiration_ms = 0
        return {"history_id": history_id, "expiration_ms": expiration_ms}

    def stop_watch(self) -> None:
        self._request("POST", "users/me/stop")

    def list_message_page(
        self,
        label_id: str,
        *,
        page_token: str | None = None,
        max_results: int = MAX_GMAIL_PAGE_SIZE,
    ) -> dict[str, Any]:
        _require_label_id(label_id)
        size = max(1, min(int(max_results), MAX_GMAIL_PAGE_SIZE))
        params: list[tuple[str, object]] = [
            ("labelIds", label_id),
            ("includeSpamTrash", "false"),
            ("maxResults", size),
        ]
        if page_token:
            params.append(("pageToken", page_token))
        return self._request("GET", "users/me/messages", params=params)

    def get_message_metadata(self, message_id: str, label_id: str) -> dict[str, Any]:
        _require_label_id(label_id)
        message_id = _valid_gmail_id(message_id)
        if not message_id:
            raise GoogleAlertsGmailError("gmail_message_id_invalid")
        params = [
            ("format", "metadata"),
            ("metadataHeaders", "From"),
            ("metadataHeaders", "Subject"),
            ("metadataHeaders", "Authentication-Results"),
        ]
        payload = self._request(
            "GET",
            f"users/me/messages/{quote(message_id, safe='')}",
            params=params,
        )
        labels = payload.get("labelIds", [])
        if not isinstance(labels, list) or label_id not in labels:
            raise GoogleAlertsGmailError("gmail_message_not_in_selected_label")
        return payload

    def get_verified_raw_message(self, message_id: str, label_id: str) -> bytes | None:
        """Metadata is checked first; raw bytes are never requested for other mail."""
        metadata = self.get_message_metadata(message_id, label_id)
        if not is_google_alerts_metadata(metadata.get("payload", {}).get("headers")):
            return None
        payload = self._request(
            "GET",
            f"users/me/messages/{quote(message_id, safe='')}",
            params=[("format", "raw")],
        )
        encoded = payload.get("raw")
        if not isinstance(encoded, str) or not encoded:
            raise GoogleAlertsGmailError("gmail_raw_message_missing")
        try:
            padded = encoded + ("=" * (-len(encoded) % 4))
            return base64.urlsafe_b64decode(padded.encode("ascii"))
        except Exception:
            raise GoogleAlertsGmailError("gmail_raw_message_invalid") from None

    def list_history_page(
        self,
        label_id: str,
        start_history_id: str,
        *,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        _require_label_id(label_id)
        if not isinstance(start_history_id, str) or not start_history_id.isdigit():
            raise GoogleAlertsGmailError("gmail_history_cursor_invalid")
        params: list[tuple[str, object]] = [
            ("startHistoryId", start_history_id),
            ("labelId", label_id),
            ("historyTypes", "messageAdded"),
            ("historyTypes", "labelAdded"),
            ("maxResults", MAX_GMAIL_PAGE_SIZE),
        ]
        if page_token:
            params.append(("pageToken", page_token))
        return self._request("GET", "users/me/history", params=params)


def _require_label_id(label_id: str) -> None:
    if (
        not isinstance(label_id, str)
        or not label_id
        or len(label_id) > 256
        or any(ord(ch) < 33 or ord(ch) > 126 for ch in label_id)
    ):
        raise GoogleAlertsGmailError("gmail_label_id_invalid")


def _extract_history_message_ids(payload: dict[str, Any]) -> list[str]:
    found: list[str] = []
    history = payload.get("history", [])
    if not isinstance(history, list):
        return found
    for record in history:
        if not isinstance(record, dict):
            continue
        for key in ("messagesAdded", "labelsAdded"):
            entries = record.get(key, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                message = entry.get("message") if isinstance(entry, dict) else None
                message_id = _valid_gmail_id(message.get("id")) if isinstance(message, dict) else None
                if message_id:
                    found.append(message_id)
    return list(dict.fromkeys(found))


def _stage_message_ids(
    conn: sqlite3.Connection,
    message_ids: list[str],
    *,
    history_backfill: bool,
) -> int:
    stamp = _now_iso()
    staged = 0
    for raw_id in message_ids:
        message_id = _valid_gmail_id(raw_id)
        if not message_id:
            continue
        cursor = conn.execute(
            """INSERT INTO google_alerts_gmail_messages(
                 message_id_hash,gmail_message_id,history_backfill,status,
                 attempt_count,created_at,updated_at
               ) VALUES(?,?,?,'queued',0,?,?)
               ON CONFLICT(message_id_hash) DO UPDATE SET
                 gmail_message_id=CASE
                   WHEN google_alerts_gmail_messages.status IN ('queued','retry','processing')
                   THEN COALESCE(google_alerts_gmail_messages.gmail_message_id,excluded.gmail_message_id)
                   ELSE google_alerts_gmail_messages.gmail_message_id
                 END,
                 updated_at=excluded.updated_at""",
            (_hash(message_id), message_id, int(history_backfill), stamp, stamp),
        )
        staged += max(0, int(cursor.rowcount))
    return staged


def update_watch_expiration(
    db_path: str | Path,
    expiration_ms: int,
) -> None:
    if int(expiration_ms) <= 0:
        raise GoogleAlertsGmailError("gmail_watch_expiration_invalid")
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute(
            """UPDATE google_alerts_gmail_sync_state
               SET watch_expiration_ms=?,updated_at=? WHERE singleton=1""",
            (int(expiration_ms), _now_iso()),
        )


def restart_full_backfill(
    db_path: str | Path,
    owner_user_id: int,
    label_id: str,
    baseline: dict[str, Any],
) -> None:
    """Reset a stale history cursor from a fresh profile or watch baseline."""
    _require_label_id(label_id)
    history_id = str(baseline.get("history_id") or "")
    expiration_ms = int(baseline.get("expiration_ms") or 0)
    if not history_id.isdigit() or expiration_ms < 0:
        raise GoogleAlertsGmailError("gmail_history_cursor_invalid")
    stamp = _now_iso()
    with DB_LOCK, _connect(db_path) as conn:
        cursor = conn.execute(
            """UPDATE google_alerts_gmail_sync_state
               SET owner_user_id=?,label_id=?,history_id=?,initial_history_id=?,
                   backfill_page_token=NULL,history_page_token=NULL,
                   history_start_id=NULL,history_candidate_id=NULL,
                   backfill_state='scanning',
                   watch_expiration_ms=NULLIF(?,0),last_error_code=NULL,updated_at=?
               WHERE singleton=1""",
            (int(owner_user_id), label_id, history_id, history_id, expiration_ms, stamp),
        )
        if cursor.rowcount == 0:
            conn.execute(
                """INSERT INTO google_alerts_gmail_sync_state(
                     singleton,owner_user_id,label_id,history_id,initial_history_id,
                     backfill_state,watch_expiration_ms,updated_at
                   ) VALUES(1,?,?,?,?, 'scanning',NULLIF(?,0),?)""",
                (int(owner_user_id), label_id, history_id, history_id, expiration_ms, stamp),
            )


def has_pending_push_events(db_path: str | Path) -> bool:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT 1 FROM google_alerts_gmail_push_events WHERE processed_at IS NULL LIMIT 1"
        ).fetchone() is not None


def mark_push_events_processed(db_path: str | Path) -> int:
    stamp = _now_iso()
    with DB_LOCK, _connect(db_path) as conn:
        cursor = conn.execute(
            """UPDATE google_alerts_gmail_push_events
               SET processed_at=? WHERE processed_at IS NULL""",
            (stamp,),
        )
    return max(0, int(cursor.rowcount))


def run_sync_cycle(
    db_path: str | Path,
    config: GmailIntegrationConfig,
    process_result: Callable[[int, Any, bool], None],
    *,
    now_ms: int | None = None,
    max_backfill_pages: int = 10,
    message_batch_limit: int = 25,
) -> dict[str, Any]:
    """Run one bounded owner-only sync cycle using polling or Pub/Sub push."""
    if not config.live_access_enabled:
        return {"enabled": False, "stage": "disabled"}
    access_token = refresh_access_token(db_path, config)
    client = GmailApiClient(
        access_token,
        refresh_access_token=lambda: refresh_access_token(db_path, config, force_refresh=True),
    )
    profile = client.get_profile()
    if profile["email_address"] != config.owner_email:
        raise GoogleAlertsGmailError("gmail_account_not_owner")
    label_id = client.resolve_alert_label_id()
    with _connect(db_path) as conn:
        current = conn.execute(
            """SELECT label_id,backfill_state,watch_expiration_ms,last_reconciled_at
               FROM google_alerts_gmail_sync_state WHERE singleton=1"""
        ).fetchone()

    stamp_ms = int(time.time() * 1000 if now_ms is None else now_ms)
    if current is None:
        if config.sync_mode == "push":
            if not config.pubsub_topic:
                raise GoogleAlertsGmailError("gmail_pubsub_configuration_incomplete")
            baseline = client.watch(label_id, config.pubsub_topic)
            save_sync_baseline(db_path, config.owner_user_id, label_id, baseline["history_id"], watch_expiration_ms=int(baseline["expiration_ms"]))
            watch_expiration = int(baseline["expiration_ms"])
        else:
            save_sync_baseline(db_path, config.owner_user_id, label_id, profile["history_id"])
            watch_expiration = 0
        current_state, last_reconciled = "scanning", None
    else:
        if str(current["label_id"]) != label_id:
            raise GoogleAlertsGmailError("gmail_label_changed_reconnect")
        current_state = str(current["backfill_state"])
        watch_expiration = int(current["watch_expiration_ms"] or 0)
        last_reconciled = current["last_reconciled_at"]

    if config.sync_mode == "push" and watch_expiration <= stamp_ms + 24 * 60 * 60 * 1000:
        if not config.pubsub_topic:
            raise GoogleAlertsGmailError("gmail_pubsub_configuration_incomplete")
        watch = client.watch(label_id, config.pubsub_topic)
        update_watch_expiration(db_path, int(watch["expiration_ms"]))

    stage_info: dict[str, Any] = {"staged": 0}
    if current_state in {"scanning", "not_started"}:
        for _ in range(max(1, min(int(max_backfill_pages), 25))):
            page = stage_initial_backfill_page(db_path, client)
            stage_info["staged"] += int(page["staged"])
            if page["complete"]:
                current_state = "history_catchup"
                break
    if current_state == "history_catchup":
        for _ in range(max(1, min(int(max_backfill_pages), 25))):
            try:
                catchup = stage_history_catchup(db_path, client)
            except GoogleAlertsGmailError as exc:
                if exc.status_code != 404:
                    raise
                if config.sync_mode == "push":
                    if not config.pubsub_topic:
                        raise GoogleAlertsGmailError("gmail_pubsub_configuration_incomplete")
                    baseline = client.watch(label_id, config.pubsub_topic)
                else:
                    baseline = {"history_id": client.get_profile()["history_id"]}
                restart_full_backfill(db_path, config.owner_user_id, label_id, baseline)
                current_state = "scanning"
                stage_info["history_cursor_expired"] = True
                break
            stage_info["staged"] += int(catchup["staged"])
            if catchup["complete"]:
                current_state = "draining"
                break

    message_counts = process_queued_messages(db_path, client, process_result, limit=message_batch_limit)
    sync = sync_state(db_path) or {}
    current_state = str(sync.get("backfill_state") or current_state)
    # The initial history catch-up itself records the reconciliation timestamp.
    # Reuse it so polling does not immediately repeat the same history request.
    last_reconciled = sync.get("last_reconciled_at") or last_reconciled
    if current_state == "complete":
        interval_seconds = config.poll_interval_seconds if config.sync_mode == "polling" else 15 * 60
        reconcile_due = True
        if last_reconciled:
            try:
                previous = datetime.fromisoformat(str(last_reconciled))
                if previous.tzinfo is None:
                    previous = previous.replace(tzinfo=timezone.utc)
                reconcile_due = (datetime.fromtimestamp(stamp_ms / 1000, timezone.utc) - previous).total_seconds() >= interval_seconds
            except (TypeError, ValueError, OverflowError):
                reconcile_due = True
        push_pending = config.sync_mode == "push" and has_pending_push_events(db_path)
        if push_pending or reconcile_due:
            incremental_staged = 0
            incremental_complete = False
            try:
                for _ in range(max(1, min(int(max_backfill_pages), 25))):
                    incremental = stage_incremental_history(db_path, client)
                    incremental_staged += int(incremental["staged"])
                    if incremental["complete"]:
                        incremental_complete = True
                        break
            except GoogleAlertsGmailError as exc:
                if exc.status_code != 404:
                    raise
                if config.sync_mode == "push":
                    if not config.pubsub_topic:
                        raise GoogleAlertsGmailError("gmail_pubsub_configuration_incomplete")
                    baseline = client.watch(label_id, config.pubsub_topic)
                else:
                    baseline = {"history_id": client.get_profile()["history_id"]}
                restart_full_backfill(db_path, config.owner_user_id, label_id, baseline)
                current_state = "scanning"
                stage_info["history_cursor_expired"] = True
            else:
                stage_info["incremental_staged"] = incremental_staged
                stage_info["incremental_complete"] = incremental_complete
                if incremental_complete and config.sync_mode == "push":
                    mark_push_events_processed(db_path)
                message_counts = process_queued_messages(db_path, client, process_result, limit=message_batch_limit)
    return {"enabled": True, "sync_mode": config.sync_mode, "stage": current_state, "staging": stage_info, "messages": message_counts, "sync": sync_state(db_path)}


def save_sync_baseline(
    db_path: str | Path,
    owner_user_id: int,
    label_id: str,
    history_id: str,
    *,
    watch_expiration_ms: int | None = None,
) -> None:
    """Persist the history cursor before backfill; no push watch is required."""
    _require_label_id(label_id)
    history_id = str(history_id or "")
    if not history_id.isdigit():
        raise GoogleAlertsGmailError("gmail_history_cursor_invalid")
    expiration = int(watch_expiration_ms or 0)
    if expiration < 0:
        raise GoogleAlertsGmailError("gmail_watch_expiration_invalid")
    stamp = _now_iso()
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO google_alerts_gmail_sync_state(
                 singleton,owner_user_id,label_id,history_id,initial_history_id,
                 backfill_state,watch_expiration_ms,updated_at
               ) VALUES(1,?,?,?,?,'scanning',NULLIF(?,0),?)
               ON CONFLICT(singleton) DO UPDATE SET
                 owner_user_id=excluded.owner_user_id,
                 label_id=excluded.label_id,
                 history_id=COALESCE(google_alerts_gmail_sync_state.history_id,excluded.history_id),
                 initial_history_id=COALESCE(google_alerts_gmail_sync_state.initial_history_id,excluded.initial_history_id),
                 backfill_state=CASE
                   WHEN google_alerts_gmail_sync_state.backfill_state='complete'
                   THEN 'complete'
                   ELSE google_alerts_gmail_sync_state.backfill_state
                 END,
                 watch_expiration_ms=excluded.watch_expiration_ms,
                 updated_at=excluded.updated_at""",
            (int(owner_user_id), label_id, history_id, history_id, expiration, stamp),
        )


def save_watch_baseline(
    db_path: str | Path,
    owner_user_id: int,
    label_id: str,
    watch: dict[str, Any],
) -> None:
    """Backward-compatible wrapper for push-mode tests and watch setup."""
    save_sync_baseline(
        db_path, owner_user_id, label_id, str(watch.get("history_id") or ""),
        watch_expiration_ms=int(watch.get("expiration_ms") or 0),
    )


def stage_initial_backfill_page(
    db_path: str | Path,
    client: GmailApiClient,
) -> dict[str, Any]:
    with _connect(db_path) as conn:
        state = conn.execute(
            "SELECT label_id,backfill_page_token,backfill_state FROM google_alerts_gmail_sync_state WHERE singleton=1"
        ).fetchone()
    if state is None:
        raise GoogleAlertsGmailError("gmail_watch_not_initialized")
    if state["backfill_state"] not in {"scanning", "not_started"}:
        return {"staged": 0, "complete": state["backfill_state"] != "scanning"}
    payload = client.list_message_page(
        str(state["label_id"]),
        page_token=state["backfill_page_token"],
    )
    items = payload.get("messages", [])
    message_ids = [
        str(item["id"])
        for item in items
        if isinstance(item, dict) and _valid_gmail_id(item.get("id"))
    ] if isinstance(items, list) else []
    next_token = payload.get("nextPageToken")
    if next_token is not None and (not isinstance(next_token, str) or len(next_token) > 4096):
        raise GoogleAlertsGmailError("gmail_page_token_invalid")
    stamp = _now_iso()
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        staged = _stage_message_ids(conn, message_ids, history_backfill=True)
        conn.execute(
            """UPDATE google_alerts_gmail_sync_state
               SET backfill_page_token=?,backfill_state=?,updated_at=?
               WHERE singleton=1""",
            (next_token, "scanning" if next_token else "history_catchup", stamp),
        )
    return {"staged": staged, "complete": not bool(next_token)}


def stage_history_catchup(
    db_path: str | Path,
    client: GmailApiClient,
) -> dict[str, Any]:
    with _connect(db_path) as conn:
        state = conn.execute(
            """SELECT label_id,initial_history_id,backfill_state,
                      history_page_token,history_start_id,history_candidate_id
               FROM google_alerts_gmail_sync_state WHERE singleton=1"""
        ).fetchone()
    if state is None or not state["initial_history_id"]:
        raise GoogleAlertsGmailError("gmail_watch_not_initialized")
    if state["backfill_state"] not in {"history_catchup", "draining", "complete"}:
        return {"staged": 0, "complete": False}
    if state["backfill_state"] in {"draining", "complete"}:
        return {"staged": 0, "complete": True}

    start_id = str(state["history_start_id"] or state["initial_history_id"])
    page_token = state["history_page_token"]
    payload = client.list_history_page(
        str(state["label_id"]), start_id, page_token=page_token
    )
    message_ids = _extract_history_message_ids(payload)
    candidate = payload.get("historyId")
    latest_history_id = (
        str(candidate)
        if isinstance(candidate, str) and candidate.isdigit()
        else str(state["history_candidate_id"] or start_id)
    )
    next_token = payload.get("nextPageToken")
    if next_token is not None and (
        not isinstance(next_token, str) or len(next_token) > 4096
    ):
        raise GoogleAlertsGmailError("gmail_history_page_token_invalid")

    stamp = _now_iso()
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        staged = _stage_message_ids(conn, message_ids, history_backfill=True)
        if next_token:
            conn.execute(
                """UPDATE google_alerts_gmail_sync_state
                   SET history_start_id=?,history_page_token=?,
                       history_candidate_id=?,updated_at=?
                   WHERE singleton=1""",
                (start_id, next_token, latest_history_id, stamp),
            )
            complete = False
        else:
            conn.execute(
                """UPDATE google_alerts_gmail_sync_state
                   SET history_id=?,history_page_token=NULL,history_start_id=NULL,
                       history_candidate_id=NULL,backfill_state='draining',
                       last_reconciled_at=?,updated_at=?
                   WHERE singleton=1""",
                (latest_history_id, stamp, stamp),
            )
            complete = True
    return {
        "staged": staged,
        "complete": complete,
        "history_id": latest_history_id,
    }


def stage_incremental_history(
    db_path: str | Path,
    client: GmailApiClient,
) -> dict[str, Any]:
    with _connect(db_path) as conn:
        state = conn.execute(
            """SELECT label_id,history_id,backfill_state,
                      history_page_token,history_start_id,history_candidate_id
               FROM google_alerts_gmail_sync_state WHERE singleton=1"""
        ).fetchone()
    if state is None or not state["history_id"]:
        raise GoogleAlertsGmailError("gmail_history_cursor_missing")
    if state["backfill_state"] != "complete":
        raise GoogleAlertsGmailError("gmail_backfill_not_complete")

    start_id = str(state["history_start_id"] or state["history_id"])
    page_token = state["history_page_token"]
    payload = client.list_history_page(
        str(state["label_id"]), start_id, page_token=page_token
    )
    message_ids = _extract_history_message_ids(payload)
    candidate = payload.get("historyId")
    latest_history_id = (
        str(candidate)
        if isinstance(candidate, str) and candidate.isdigit()
        else str(state["history_candidate_id"] or start_id)
    )
    next_token = payload.get("nextPageToken")
    if next_token is not None and (
        not isinstance(next_token, str) or len(next_token) > 4096
    ):
        raise GoogleAlertsGmailError("gmail_history_page_token_invalid")

    stamp = _now_iso()
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        staged = _stage_message_ids(conn, message_ids, history_backfill=False)
        if next_token:
            conn.execute(
                """UPDATE google_alerts_gmail_sync_state
                   SET history_start_id=?,history_page_token=?,
                       history_candidate_id=?,last_error_code=NULL,updated_at=?
                   WHERE singleton=1""",
                (start_id, next_token, latest_history_id, stamp),
            )
            complete = False
        else:
            conn.execute(
                """UPDATE google_alerts_gmail_sync_state
                   SET history_id=?,history_page_token=NULL,history_start_id=NULL,
                       history_candidate_id=NULL,last_reconciled_at=?,
                       last_error_code=NULL,updated_at=?
                   WHERE singleton=1""",
                (latest_history_id, stamp, stamp),
            )
            complete = True
    return {
        "staged": staged,
        "history_id": latest_history_id if complete else str(state["history_id"]),
        "complete": complete,
    }


def process_queued_messages(
    db_path: str | Path,
    client: GmailApiClient,
    process_result: Callable[[int, Any, bool], None],
    *,
    limit: int = 10,
) -> dict[str, int]:
    """Process label-scoped messages without persisting raw MIME or snippets."""
    batch = max(0, min(int(limit), 50))
    counts = {"processed": 0, "skipped": 0, "retry": 0, "dead": 0}
    if batch == 0:
        return counts
    with DB_LOCK, _connect(db_path) as conn:
        rows = conn.execute(
            """SELECT m.message_id_hash,m.gmail_message_id,m.history_backfill,
                      s.owner_user_id,s.label_id
               FROM google_alerts_gmail_messages m
               CROSS JOIN google_alerts_gmail_sync_state s
               WHERE m.status='queued'
                  OR (m.status='retry' AND m.next_attempt_at<=?)
               ORDER BY m.created_at,m.message_id_hash LIMIT ?""",
            (_now_iso(), batch),
        ).fetchall()
        claimed: list[dict[str, Any]] = []
        for row in rows:
            if not row["gmail_message_id"]:
                conn.execute(
                    "UPDATE google_alerts_gmail_messages SET status='dead',error_code='message_id_missing',updated_at=? WHERE message_id_hash=?",
                    (_now_iso(), row["message_id_hash"]),
                )
                counts["dead"] += 1
                continue
            conn.execute(
                """UPDATE google_alerts_gmail_messages
                   SET status='processing',attempt_count=attempt_count+1,updated_at=?
                   WHERE message_id_hash=?""",
                (_now_iso(), row["message_id_hash"]),
            )
            claimed.append(dict(row))

    for item in claimed:
        try:
            raw = client.get_verified_raw_message(
                str(item["gmail_message_id"]), str(item["label_id"])
            )
            if raw is None:
                _mark_message_terminal(db_path, item["message_id_hash"], "skipped", "not_google_alerts")
                counts["skipped"] += 1
                continue
            parsed = parse_google_alert_email(raw)
            for result in parsed.results:
                process_result(
                    int(item["owner_user_id"]),
                    result,
                    bool(item["history_backfill"]),
                )
            _mark_message_terminal(
                db_path,
                item["message_id_hash"],
                "processed",
                None,
                result_count=len(parsed.results),
            )
            counts["processed"] += 1
        except GoogleAlertEmailError as exc:
            _mark_message_terminal(db_path, item["message_id_hash"], "skipped", exc.code)
            counts["skipped"] += 1
        except GoogleAlertsGmailError as exc:
            _retry_or_dead(db_path, item["message_id_hash"], exc.code, exc.retryable)
            counts["retry" if exc.retryable else "dead"] += 1
        except Exception:
            _retry_or_dead(db_path, item["message_id_hash"], "processor_error", True)
            counts["retry"] += 1
    _mark_backfill_complete_if_drained(db_path)
    return counts


def _mark_message_terminal(
    db_path: str | Path,
    message_hash: str,
    status: str,
    error_code: str | None,
    *,
    result_count: int = 0,
) -> None:
    if status not in {"processed", "skipped", "dead"}:
        raise ValueError("Invalid terminal Gmail message state.")
    with DB_LOCK, _connect(db_path) as conn:
        conn.execute(
            """UPDATE google_alerts_gmail_messages
               SET gmail_message_id=NULL,status=?,error_code=?,result_count=?,
                   processed_at=?,updated_at=?
               WHERE message_id_hash=?""",
            (status, error_code, int(result_count), _now_iso(), _now_iso(), message_hash),
        )


def _retry_or_dead(
    db_path: str | Path,
    message_hash: str,
    error_code: str,
    retryable: bool,
) -> None:
    with DB_LOCK, _connect(db_path) as conn:
        row = conn.execute(
            "SELECT attempt_count FROM google_alerts_gmail_messages WHERE message_id_hash=?",
            (message_hash,),
        ).fetchone()
        attempts = int(row["attempt_count"] or 0) if row else MAX_MESSAGE_ATTEMPTS
        if not retryable or attempts >= MAX_MESSAGE_ATTEMPTS:
            status, retry_at = "dead", None
        else:
            status = "retry"
            delay = min(3600, 30 * (2 ** max(0, attempts - 1)))
            retry_at = datetime.fromtimestamp(
                time.time() + delay, tz=timezone.utc
            ).isoformat()
        conn.execute(
            """UPDATE google_alerts_gmail_messages
               SET status=?,next_attempt_at=?,error_code=?,updated_at=?
               WHERE message_id_hash=?""",
            (status, retry_at, error_code, _now_iso(), message_hash),
        )


def _mark_backfill_complete_if_drained(db_path: str | Path) -> bool:
    stamp = _now_iso()
    with DB_LOCK, _connect(db_path) as conn:
        state = conn.execute(
            "SELECT backfill_state FROM google_alerts_gmail_sync_state WHERE singleton=1"
        ).fetchone()
        if state is None or state["backfill_state"] != "draining":
            return False
        pending = conn.execute(
            """SELECT 1 FROM google_alerts_gmail_messages
               WHERE history_backfill=1 AND status IN ('queued','processing','retry')
               LIMIT 1"""
        ).fetchone()
        if pending:
            return False
        conn.execute(
            """UPDATE google_alerts_gmail_sync_state
               SET backfill_state='complete',backfill_page_token=NULL,
                   last_error_code=NULL,updated_at=? WHERE singleton=1""",
            (stamp,),
        )
        return True


def store_pubsub_push(
    db_path: str | Path,
    *,
    subscription: str,
    expected_subscription: str,
    pubsub_message_id: str,
    history_id: str,
    email_address: str,
) -> bool:
    """Persist only message ID + history cursor; never store push payload/email."""
    if subscription != expected_subscription:
        raise GoogleAlertsGmailError("gmail_pubsub_subscription_mismatch")
    if not isinstance(pubsub_message_id, str) or not pubsub_message_id or len(pubsub_message_id) > 256:
        raise GoogleAlertsGmailError("gmail_pubsub_message_id_invalid")
    if not isinstance(history_id, str) or not history_id.isdigit():
        raise GoogleAlertsGmailError("gmail_pubsub_history_id_invalid")
    with _connect(db_path) as conn:
        creds = conn.execute(
            "SELECT owner_user_id,account_email_hash FROM google_alerts_gmail_credentials WHERE singleton=1"
        ).fetchone()
    if creds is None or _hash(str(email_address or "").strip().casefold()) != creds["account_email_hash"]:
        raise GoogleAlertsGmailError("gmail_pubsub_mailbox_mismatch")
    with DB_LOCK, _connect(db_path) as conn:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO google_alerts_gmail_push_events(
                 pubsub_message_id,history_id,received_at
               ) VALUES(?,?,?)""",
            (pubsub_message_id, history_id, _now_iso()),
        )
    return cursor.rowcount > 0


def verify_pubsub_oidc_token(
    authorization_header: str,
    *,
    audience: str,
    expected_service_account_email: str,
) -> bool:
    """Verify Google's signed push identity token with audience and email checks."""
    if not isinstance(authorization_header, str):
        return False
    prefix, _, token = authorization_header.partition(" ")
    if prefix.casefold() != "bearer" or not token or len(token) > 16384:
        return False
    try:
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token

        claims = id_token.verify_oauth2_token(token, GoogleRequest(), audience=audience)
    except Exception:
        return False
    return (
        claims.get("email_verified") is True
        and str(claims.get("email") or "").casefold()
        == expected_service_account_email.casefold()
        and str(claims.get("iss") or "") in {
            "accounts.google.com",
            "https://accounts.google.com",
        }
    )


def decode_pubsub_push(body: bytes) -> dict[str, str]:
    """Decode the small Pub/Sub envelope into sanitized identifiers."""
    if not isinstance(body, bytes) or not body or len(body) > MAX_PUSH_BODY_BYTES:
        raise GoogleAlertsGmailError("gmail_pubsub_payload_invalid")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise GoogleAlertsGmailError("gmail_pubsub_payload_invalid") from None
    message = payload.get("message") if isinstance(payload, dict) else None
    subscription = payload.get("subscription") if isinstance(payload, dict) else None
    if not isinstance(message, dict) or not isinstance(subscription, str):
        raise GoogleAlertsGmailError("gmail_pubsub_payload_invalid")
    message_id = message.get("messageId")
    data = message.get("data")
    if not isinstance(message_id, str) or not message_id or len(message_id) > 256:
        raise GoogleAlertsGmailError("gmail_pubsub_message_id_invalid")
    if not isinstance(data, str) or not data or len(data) > MAX_PUSH_BODY_BYTES:
        raise GoogleAlertsGmailError("gmail_pubsub_data_invalid")
    try:
        padded = data + ("=" * (-len(data) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        notification = json.loads(decoded.decode("utf-8"))
    except Exception:
        raise GoogleAlertsGmailError("gmail_pubsub_data_invalid") from None
    if not isinstance(notification, dict):
        raise GoogleAlertsGmailError("gmail_pubsub_data_invalid")
    email_address = notification.get("emailAddress")
    history_id = notification.get("historyId")
    if not isinstance(email_address, str) or not isinstance(history_id, str) or not history_id.isdigit():
        raise GoogleAlertsGmailError("gmail_pubsub_data_invalid")
    return {
        "subscription": subscription,
        "pubsub_message_id": message_id,
        "history_id": history_id,
        "email_address": email_address.casefold(),
    }


def disconnect(
    db_path: str | Path,
    config: GmailIntegrationConfig,
    *,
    session: requests.Session | None = None,
) -> None:
    """Revoke the owner grant and remove Gmail-only rows/checkpoints locally.

    Public jobs reused by a Gmail observation remain intact. Already-sent
    notification records are retained only when their candidate is a public
    job; pending Gmail historical rows are cancelled before private jobs are
    removed.
    """
    clear_access_token_cache(db_path, config.owner_user_id)
    refresh_token = None
    try:
        refresh_token = load_refresh_token(db_path, config.owner_user_id, config)
    except GoogleAlertsGmailError:
        pass
    if refresh_token:
        # Stop Gmail push delivery before revoking the grant. If the access
        # token is already invalid or the network is unavailable, local data
        # deletion still proceeds and the watch naturally expires within 7 days.
        if config.sync_mode == "push":
            try:
                access_token = refresh_access_token(db_path, config, session=session)
                GmailApiClient(access_token).stop_watch()
            except GoogleAlertsGmailError:
                pass

        client = session or requests
        try:
            client.post(
                GOOGLE_REVOKE_ENDPOINT,
                data={"token": refresh_token},
                timeout=(5, 10),
            )
        except requests.RequestException:
            # Local disconnect must still erase the retained credential.
            pass

    with DB_LOCK, _connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        private_rows = conn.execute(
            """SELECT DISTINCT j.id,j.canonical_opportunity_id
               FROM jobs j
               LEFT JOIN google_alerts_gmail_opportunities go
                 ON go.candidate_job_id=j.id AND go.user_id=?
               WHERE j.source='google_alerts_gmail'
                 AND j.source_owner_user_id=?""",
            (int(config.owner_user_id), int(config.owner_user_id)),
        ).fetchall()
        private_job_ids = [int(row["id"]) for row in private_rows]
        private_canonical_ids = list(dict.fromkeys(
            int(row["canonical_opportunity_id"])
            for row in private_rows
            if row["canonical_opportunity_id"] is not None
        ))

        if private_job_ids:
            job_marks = ",".join("?" for _ in private_job_ids)
            tables = {
                str(row[0]) for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "user_applications" in tables:
                conn.execute(
                    f"DELETE FROM user_applications WHERE user_id=? AND job_id IN ({job_marks})",
                    (int(config.owner_user_id), *private_job_ids),
                )
            if "user_job_evaluations" in tables:
                conn.execute(
                    f"DELETE FROM user_job_evaluations WHERE user_id=? AND job_id IN ({job_marks})",
                    (int(config.owner_user_id), *private_job_ids),
                )

        if "user_notification_ledger" in {
            str(row[0]) for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            conn.execute(
                """UPDATE user_notification_ledger
                   SET status='cancelled',backlog_override=0,claimed_at=NULL,
                       next_attempt_at=NULL,last_error='gmail_disconnected',updated_at=?
                   WHERE user_id=? AND backlog_override=1
                     AND status IN ('queued','failed','sending')""",
                (_now_iso(), int(config.owner_user_id)),
            )

        # Clear references before removing private jobs.
        for table in (
            "google_alerts_gmail_opportunities",
            "google_alerts_gmail_push_events",
            "google_alerts_gmail_messages",
            "google_alerts_gmail_sync_state",
            "google_alerts_gmail_oauth_states",
            "google_alerts_gmail_credentials",
        ):
            conn.execute(f"DELETE FROM {table}")

        if private_job_ids:
            marks = ",".join("?" for _ in private_job_ids)
            conn.execute(
                f"DELETE FROM jobs WHERE id IN ({marks}) AND source_owner_user_id=?",
                (*private_job_ids, int(config.owner_user_id)),
            )
            if private_canonical_ids:
                marks = ",".join("?" for _ in private_canonical_ids)
                conn.execute(
                    f"""DELETE FROM canonical_opportunities
                        WHERE id IN ({marks})
                          AND NOT EXISTS (
                            SELECT 1 FROM jobs
                            WHERE jobs.canonical_opportunity_id=canonical_opportunities.id
                          )""",
                    tuple(private_canonical_ids),
                )


def has_credentials(db_path: str | Path) -> bool:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT 1 FROM google_alerts_gmail_credentials WHERE singleton=1"
        ).fetchone() is not None


def sync_state(db_path: str | Path) -> dict[str, Any] | None:
    """Return operational status without mailbox address, message IDs or tokens."""
    with _connect(db_path) as conn:
        state = conn.execute(
            """SELECT backfill_state,watch_expiration_ms,last_reconciled_at,
                      last_error_code,updated_at
               FROM google_alerts_gmail_sync_state WHERE singleton=1"""
        ).fetchone()
        if state is None:
            return None
        counts = {
            str(row["status"]): int(row["n"])
            for row in conn.execute(
                "SELECT status,COUNT(*) AS n FROM google_alerts_gmail_messages GROUP BY status"
            ).fetchall()
        }
        return {**dict(state), "message_counts": counts}
