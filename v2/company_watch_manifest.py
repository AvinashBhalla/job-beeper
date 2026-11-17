"""Strict parser for the curated Company Watch manifest.

The manifest is evidence for review, never an activation allowlist. This module
performs deterministic local validation only; it makes no network requests.
"""
from __future__ import annotations

import csv
import hashlib
import ipaddress
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

EXPECTED_ROWS = 100
REQUIRED_COLUMNS = (
    "no", "name", "sector", "country", "careers_url", "board_type",
    "scan_mode", "scan_enabled", "verification_status",
    "verification_source", "verification_note",
)
SUPPORTED_PROVIDERS = frozenset({
    "greenhouse", "ashby", "lever", "smartrecruiters", "workday",
    "workable", "keka", "darwinbox",
})
AMBIGUOUS_STATUSES = frozenset({
    "partial_entity_match",
    "identity_needs_confirmation",
    "identity_confirmed_board_unverified",
    "official_homepage_no_careers_page_found",
    "company_career_portal_needs_validation",
    "verified_workday_board_needs_adapter",
    "verified_workable_board",
})


def _https_url(value: str, field: str) -> str:
    value = str(value or "").strip()
    if not value or len(value) > 2048 or any(character.isspace() for character in value):
        raise ValueError(f"{field} must be a non-empty URL without whitespace and at most 2,048 characters")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{field} is malformed") from exc
    if (
        parsed.scheme.lower() != "https" or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
        or port not in (None, 443)
    ):
        raise ValueError(f"{field} must be an HTTPS URL without credentials or a custom port")
    host = parsed.hostname.lower().rstrip(".")
    if (
        host in {"localhost", "localhost.localdomain"}
        or host.endswith((".localhost", ".local", ".internal"))
        or "." not in host
    ):
        raise ValueError(f"{field} must use a non-local hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError(f"{field} must not point to a private or reserved IP address")
    return value


def parse_manifest(
    path: str | Path,
    normalize_candidate_url: Callable[[Any], dict[str, str]],
    *,
    expected_rows: int = EXPECTED_ROWS,
) -> dict[str, Any]:
    """Parse, validate and classify all manifest rows without mutating state."""
    path = Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
        raise ValueError("Company Watch manifest columns do not match the required schema")
    rows = list(reader)
    if expected_rows is not None and len(rows) != expected_rows:
        raise ValueError(f"Expected {expected_rows} manifest rows; found {len(rows)}")

    seen_numbers: set[int] = set()
    seen_names: set[str] = set()
    parsed_rows: list[dict[str, Any]] = []
    for line_number, raw_row in enumerate(rows, start=2):
        if None in raw_row or any(value is None for value in raw_row.values()):
            raise ValueError(f"CSV line {line_number}: row has missing or extra columns")
        row = {key: str(raw_row.get(key) or "").strip() for key in REQUIRED_COLUMNS}
        try:
            row_number = int(row["no"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"CSV line {line_number}: no must be an integer") from exc
        if row_number < 1 or row_number in seen_numbers:
            raise ValueError(f"CSV line {line_number}: duplicate or invalid row number")
        seen_numbers.add(row_number)
        if not row["name"] or len(row["name"]) > 160:
            raise ValueError(f"CSV line {line_number}: company name is required and limited to 160 characters")
        name_key = re.sub(r"\s+", " ", row["name"]).casefold()
        if name_key in seen_names:
            raise ValueError(f"CSV line {line_number}: duplicate company name")
        seen_names.add(name_key)
        careers_url = _https_url(row["careers_url"], f"row {row_number} careers_url")
        enabled_value = row["scan_enabled"].casefold()
        if enabled_value not in {"true", "false"}:
            raise ValueError(f"row {row_number}: scan_enabled must be true or false")
        enabled = enabled_value == "true"
        status = row["verification_status"].casefold()
        scan_mode = row["scan_mode"].casefold()
        board_type = row["board_type"].casefold()
        classification = "manual_review"
        reason = ""
        candidate = None

        source = row["verification_source"]
        if source:
            source = _https_url(source, f"row {row_number} verification_source")
        source_host = (urlsplit(source).hostname or "").casefold() if source else ""
        search_pointer = source_host in {"google.com", "www.google.com", "bing.com", "www.bing.com"}
        identity_ambiguous = status in AMBIGUOUS_STATUSES or search_pointer

        reasons: list[str] = []
        if not enabled:
            reasons.append("manifest_disabled")
        if scan_mode == "manual_review" or board_type == "manual_review":
            reasons.append("manifest_manual_review")
        if scan_mode == "careers_page" or board_type == "careers_page":
            reasons.append("generic_careers_page_requires_discovery")
        if scan_mode not in SUPPORTED_PROVIDERS and scan_mode not in {"careers_page", "manual_review"}:
            reasons.append("unsupported_scan_mode")
        if identity_ambiguous:
            reasons.append("employer_identity_requires_manual_confirmation")
        if board_type != scan_mode:
            reasons.append("board_type_scan_mode_mismatch")

        if not reasons:
            try:
                candidate = normalize_candidate_url(careers_url)
            except (TypeError, ValueError) as exc:
                reasons.append(f"invalid_or_unsupported_ats_url: {str(exc)[:140]}")
            else:
                if candidate.get("provider") != scan_mode:
                    candidate = None
                    reasons.append("ats_provider_does_not_match_manifest")
                else:
                    classification = "candidate_staged"
                    reasons.append("ats_url_parsed; employer_identity_and_board_ownership_still_require_review")
        reason = ";".join(reasons)

        parsed_rows.append({
            "row_number": row_number,
            "company_name": row["name"],
            "sector": row["sector"],
            "country": row["country"],
            "careers_url": careers_url,
            "board_type": board_type,
            "scan_mode": scan_mode,
            "scan_enabled": int(enabled),
            "verification_status": row["verification_status"],
            "verification_source": source,
            "verification_note": row["verification_note"],
            "classification": classification,
            "review_reason": reason,
            "candidate": candidate,
            # Manifest evidence is not a live endpoint probe or employer-domain
            # verification, so every imported candidate starts at low confidence.
            "candidate_confidence": "low",
        })

    if seen_numbers != set(range(1, len(rows) + 1)):
        raise ValueError("Manifest row numbers must be a contiguous sequence starting at 1")

    identities: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in parsed_rows:
        candidate = row["candidate"]
        if candidate:
            key = (
                str(candidate["provider"]),
                str(candidate["candidate_host"]).casefold(),
                str(candidate["board_key"]).casefold(),
            )
            identities.setdefault(key, []).append(row)
    for collisions in identities.values():
        company_names = {row["company_name"].casefold() for row in collisions}
        if len(company_names) > 1:
            for row in collisions:
                row["candidate"] = None
                row["classification"] = "manual_review"
                row["review_reason"] += ";duplicate_ats_board_identity_across_companies"

    counts: dict[str, int] = {}
    for row in parsed_rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    return {
        "manifest_sha256": digest,
        "rows_total": len(parsed_rows),
        "rows": parsed_rows,
        "counts": counts,
    }
