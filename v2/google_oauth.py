"""Google OpenID Connect authorization helpers for public beta signup."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

import requests

from v2.sqlite_store import connect as connect_sqlite

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class GoogleOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str


def load_config() -> GoogleOAuthConfig | None:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    if not (client_id and client_secret and redirect_uri):
        return None

    parsed = urlsplit(redirect_uri)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
    if (
        parsed.scheme != "https" and not local_http
        or not parsed.netloc
        or parsed.username or parsed.password
        or parsed.query or parsed.fragment
        or parsed.path != "/api/auth/google/callback"
    ):
        raise ValueError("Google OAuth redirect URI must be HTTPS and use the registered callback path.")
    return GoogleOAuthConfig(client_id, client_secret, redirect_uri)


def _connect(db_path):
    conn = connect_sqlite(db_path)
    return conn


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _new_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def create_authorization_url(db_path, config: GoogleOAuthConfig) -> str:
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = _new_code_verifier()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    now = time.time()

    with _connect(db_path) as conn:
        conn.execute("DELETE FROM google_oauth_states WHERE expires_at<=?", (now,))
        conn.execute(
            """INSERT INTO google_oauth_states
               (state_hash, nonce, code_verifier, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?)""",
            (_hash(state), nonce, verifier, now, now + STATE_TTL_SECONDS),
        )

    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


def consume_authorization_state(db_path, state: str) -> tuple[str, str] | None:
    if not isinstance(state, str) or not state or len(state) > 512:
        return None
    now = time.time()
    with _connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """SELECT nonce, code_verifier FROM google_oauth_states
               WHERE state_hash=? AND expires_at>?""",
            (_hash(state), now),
        ).fetchone()
        conn.execute("DELETE FROM google_oauth_states WHERE state_hash=?", (_hash(state),))
        conn.execute("DELETE FROM google_oauth_states WHERE expires_at<=?", (now,))
    return (str(row[0]), str(row[1])) if row else None


def exchange_code_for_identity(code: str, verifier: str, config: GoogleOAuthConfig) -> dict:
    if not isinstance(code, str) or not code or len(code) > 4096:
        raise ValueError("Google authorization code is invalid.")
    response = requests.post(
        GOOGLE_TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        },
        timeout=(5, 15),
    )
    if response.status_code != 200:
        raise ValueError("Google sign-in could not be completed.")
    token_payload = response.json()
    id_token = token_payload.get("id_token") if isinstance(token_payload, dict) else None
    if not isinstance(id_token, str) or not id_token:
        raise ValueError("Google did not return a valid identity token.")

    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token as google_id_token

    claims = google_id_token.verify_oauth2_token(
        id_token, GoogleRequest(), audience=config.client_id
    )
    email = claims.get("email")
    subject = claims.get("sub")
    if (
        not isinstance(email, str)
        or claims.get("email_verified") is not True
        or not isinstance(subject, str)
        or not subject
    ):
        raise ValueError("Google must provide a verified email address.")
    return {"email": email, "subject": subject, "claims": claims}


def validate_nonce(claims: dict, expected_nonce: str) -> bool:
    actual_nonce = claims.get("nonce")
    return isinstance(actual_nonce, str) and hmac.compare_digest(actual_nonce, expected_nonce)
