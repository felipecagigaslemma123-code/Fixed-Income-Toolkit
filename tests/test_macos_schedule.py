"""Static contract tests for the owner-approved local macOS schedule."""

from __future__ import annotations

import plistlib
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


class MacOsScheduleTests(unittest.TestCase):
    def test_launch_agent_starts_every_day_at_0930(self) -> None:
        path = _REPO_ROOT / "tools" / "com.fixedincome.morningsync.plist"
        with path.open("rb") as source:
            configuration = plistlib.load(source)

        self.assertEqual(
            configuration["StartCalendarInterval"], {"Hour": 9, "Minute": 30}
        )
        self.assertFalse(configuration["RunAtLoad"])
        self.assertEqual(configuration["ProgramArguments"][0], "/usr/bin/open")
        self.assertIn("-gj", configuration["ProgramArguments"])
        self.assertTrue(
            configuration["ProgramArguments"][-1].endswith(
                "tools/morning_sync.command"
            )
        )

    def test_launch_agent_runs_continuous_daily_and_fifteen_minute_scheduler(self) -> None:
        wrapper = (_REPO_ROOT / "tools" / "morning_sync.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("tools/run_treasury_bill_scheduler.py", wrapper)
        self.assertIn("--environment PROD --allow-production", wrapper)
        self.assertNotIn("tools/sync_once.py", wrapper)

        scheduler = (
            _REPO_ROOT / "tools" / "run_treasury_bill_scheduler.py"
        ).read_text(encoding="utf-8")
        self.assertIn("A3: 15m", scheduler)
        self.assertIn("Treasury: 24h", scheduler)
        self.assertIn("fcntl.LOCK_EX | fcntl.LOCK_NB", scheduler)

    def test_local_launchers_use_declared_python_39_and_avoid_duplicate_scheduler(self) -> None:
        wrapper = (_REPO_ROOT / "tools" / "morning_sync.sh").read_text(
            encoding="utf-8"
        )
        launcher = (_REPO_ROOT / "Abrir Modelo LECAP BONCAP.command").read_text(
            encoding="utf-8"
        )
        self.assertIn("sys.version_info >= (3, 9)", wrapper)
        self.assertIn('".venv/bin/python"', wrapper)
        self.assertIn("sys.version_info >= (3, 9)", launcher)
        self.assertIn("--external-scheduler", launcher)


if __name__ == "__main__":
    unittest.main()
