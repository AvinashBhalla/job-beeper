"""Seed deterministic demo jobs into the isolated multi-user feature database only."""
from __future__ import annotations

import os
import sys

from v2 import radar


def main() -> int:
    if os.getenv("JOB_BEEPER_FEATURE_DEMO", "").strip().lower() != "true":
        print(
            "Refusing to seed demo jobs: set JOB_BEEPER_FEATURE_DEMO=true in the isolated feature environment.",
            file=sys.stderr,
        )
        return 2

    radar.init_db()
    demo_jobs = [
        radar.normalize_job(
            "naukri",
            "jobbeeper-demo-python-001",
            "JobBeeper Demo Labs",
            "Python Developer",
            "Bengaluru, Karnataka, India",
            "https://example.com/demo/python-developer-001",
            None,
            "unknown",
            "Demo role for validating personalized matching. Build Python backend services with Django, REST APIs and PostgreSQL.",
        ),
        radar.normalize_job(
            "naukri",
            "jobbeeper-demo-backend-002",
            "JobBeeper Demo Labs",
            "Backend Engineer",
            "Gurugram, Haryana, India",
            "https://example.com/demo/backend-engineer-002",
            None,
            "unknown",
            "Demo role for validating location and skill matching. Build backend APIs using Python, FastAPI and Redis.",
        ),
        radar.normalize_job(
            "naukri",
            "jobbeeper-demo-qa-003",
            "JobBeeper Demo Labs",
            "QA Automation Engineer",
            "Pune, Maharashtra, India",
            "https://example.com/demo/qa-automation-003",
            None,
            "unknown",
            "Demo role for validating alternate role profiles. Write automated tests with Python, Playwright and CI pipelines.",
        ),
        radar.normalize_job(
            "naukri",
            "jobbeeper-demo-frontend-004",
            "JobBeeper Demo Labs",
            "Frontend Developer",
            "Remote, India",
            "https://example.com/demo/frontend-developer-004",
            None,
            "unknown",
            "Demo role for remote matching. Build accessible React and TypeScript interfaces.",
        ),
    ]
    inserted = radar.upsert_jobs(demo_jobs, radar.get_config())
    print(f"Demo jobs processed: {len(demo_jobs)}; newly inserted: {inserted}")
    print("These are synthetic demo listings, not real vacancies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
