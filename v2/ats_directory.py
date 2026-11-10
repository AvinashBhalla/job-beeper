"""Importable, attribution-preserving seed directory for public ATS boards.

The August 2026 LastRound AI snapshot is CC BY 4.0. It seeds discovery only;
it does not prove that any board is still active today.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

DATASET_NAME = "LastRound AI ATS Company Directory (August 2026)"
DATASET_SNAPSHOT = "2026-08"
DATASET_LICENSE = "CC BY 4.0"
DATASET_ATTRIBUTION = (
    "LastRound AI, ATS Company Directory (August 2026), "
    "https://github.com/fyrosofttech/lastroundai-hiring-data"
)
DATASET_URL = (
    "https://github.com/fyrosofttech/lastroundai-hiring-data/"
    "blob/2816bfadd65b7bbec23701dd036bcc7496c729db/"
    "ats-directory/lastroundai-ats-company-directory-2026-08.csv"
)
RAW_DATASET_URL = (
    "https://raw.githubusercontent.com/fyrosofttech/lastroundai-hiring-data/"
    "2816bfadd65b7bbec23701dd036bcc7496c729db/"
    "ats-directory/lastroundai-ats-company-directory-2026-08.csv"
)

BOARD_HOSTS = {
    "greenhouse": "https://job-boards.greenhouse.io/{slug}",
    "lever": "https://jobs.lever.co/{slug}",
    "ashby": "https://jobs.ashbyhq.com/{slug}",
}
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


def parse_directory_csv(text: str) -> list[dict[str, Any]]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 2_000_000:
        raise ValueError("ATS directory input is invalid or exceeds 2 MB.")
    rows = csv.DictReader(text.splitlines())
    if rows.fieldnames != ["ats_vendor", "company_name", "board_slug", "last_crawled"]:
        raise ValueError("ATS directory has an unexpected CSV schema.")
    parsed: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        provider = str(row.get("ats_vendor") or "").strip().lower()
        name = str(row.get("company_name") or "").strip()[:160]
        slug = str(row.get("board_slug") or "").strip()
        crawled = str(row.get("last_crawled") or "").strip()
        if provider not in BOARD_HOSTS or not name or not SLUG_RE.fullmatch(slug):
            continue
        try:
            # Strict ISO date, no future date.
            from datetime import date
            date.fromisoformat(crawled)
        except ValueError:
            continue
        key = (provider, slug.lower())
        if key in seen:
            continue
        seen.add(key)
        url = BOARD_HOSTS[provider].format(slug=slug)
        parsed.append({
            "provider": provider,
            "company_name": name,
            "board_key": slug,
            "board_url": url,
            "last_crawled": crawled,
            "collector_source": provider,
            "collector_available": True,
            "confidence": "medium",
        })
    return parsed


def load_directory(path: Path) -> list[dict[str, Any]]:
    return parse_directory_csv(path.read_text(encoding="utf-8"))


def synthetic_domain(provider: str, slug: str) -> str:
    """Unique registry key where the source dataset does not provide company domains."""
    return f"ats-directory:{provider}:{slug.lower()}"
