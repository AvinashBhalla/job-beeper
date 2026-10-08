                radar.DB_PATH = original_db


    def test_jobs_today_only_filters_before_ist_midnight(self):
        from datetime import timedelta

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                day_start = radar.current_day_start_utc()

                old_job = normalize_job(
                    "linkedin",
                    "li-old-day",
                    "Acme",
                    "Software Engineer",
                    "Bengaluru",
                    "https://linkedin.com/jobs/view/old-day",
                    day_start - timedelta(minutes=30),
                    "minute",
                    "2 years experience",
                )
                new_job = normalize_job(
                    "linkedin",
                    "li-new-day",
                    "Acme",
                    "Software Engineer",
                    "Bengaluru",
                    "https://linkedin.com/jobs/view/new-day",
                    day_start + timedelta(minutes=30),
                    "minute",
                    "2 years experience",
                )

                # today_only is based on discovery lifecycle, not source
                # posting time. Explicitly move the synthetic discoveries
                # across the IST-midnight boundary.
                old_job["discovered_at"] = radar.iso(day_start - timedelta(minutes=30))
                new_job["discovered_at"] = radar.iso(day_start + timedelta(minutes=30))
                config = {
                    **BASE_CONFIG,
                    "require_explicit_experience_for_alerts": False,
                }
                self.assertEqual(upsert_jobs([old_job, new_job], config), 2)

                result = radar.jobs(today_only=True, limit=100)
                ids = {row["source_job_id"] for row in result["jobs"]}

                self.assertNotIn("li-old-day", ids)
                self.assertIn("li-new-day", ids)

                opportunities = radar.opportunities(today_only=True, limit=100)
                opportunity_ids = {
                    row["representative_job_id"]
                    for row in opportunities["opportunities"]
                }
                self.assertNotIn(1, opportunity_ids)
                self.assertIn(2, opportunity_ids)
            finally:
                radar.DB_PATH = original_db

    def test_daily_reset_uses_ist_midnight(self):
        start = current_day_start_utc()
        local = start.astimezone(radar.IST)
        self.assertEqual(local.hour, 0)
        self.assertEqual(local.minute, 0)
        self.assertEqual(local.second, 0)

    def test_telegram_timestamp_is_human_readable_ist(self):
        self.assertEqual(
            _format_timestamp("2026-10-08T07:30:50.260596+00:00"),
            "08 Oct 2026, 1:00 PM IST",
        )