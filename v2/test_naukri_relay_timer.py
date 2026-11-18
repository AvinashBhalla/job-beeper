"""Static contract tests for the production Naukri relay systemd units."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMER_PATH = ROOT / "deploy" / "systemd" / "job-radar-naukri-relay.timer"
SERVICE_PATH = ROOT / "deploy" / "systemd" / "job-radar-naukri-relay.service"


class NaukriRelayTimerUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.timer = TIMER_PATH.read_text(encoding="utf-8")
        cls.service = SERVICE_PATH.read_text(encoding="utf-8")

    def test_timer_uses_five_minute_calendar_cadence(self):
        self.assertIn("OnCalendar=*-*-* *:0/5:00", self.timer)

    def test_timer_catches_up_after_downtime(self):
        self.assertIn("Persistent=true", self.timer)

    def test_timer_avoids_monotonic_only_repeat_schedule(self):
        self.assertNotIn("OnUnitActiveSec=", self.timer)
        self.assertNotIn("OnUnitInactiveSec=", self.timer)
        self.assertNotIn("OnBootSec=", self.timer)

    def test_timer_targets_the_expected_oneshot_service(self):
        self.assertIn("Unit=job-radar-naukri-relay.service", self.timer)

    def test_service_dispatches_only_the_public_relay_workflow(self):
        self.assertIn(
            "ExecStart=/usr/bin/gh workflow run naukri-relay.yml "
            "--repo AvinashBhalla/job-beeper-naukri-relay --ref main",
            self.service,
        )

    def test_service_uses_the_ubuntu_users_existing_gh_configuration(self):
        self.assertIn("User=ubuntu", self.service)
        self.assertIn("Environment=HOME=/home/ubuntu", self.service)
        self.assertIn("Environment=GH_CONFIG_DIR=/home/ubuntu/.config/gh", self.service)

    def test_service_is_bounded_and_waits_for_network(self):
        self.assertIn("After=network-online.target", self.service)
        self.assertIn("TimeoutStartSec=300", self.service)


if __name__ == "__main__":
    unittest.main()
