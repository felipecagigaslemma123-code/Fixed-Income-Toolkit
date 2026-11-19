"""Deterministic tests for the approved daily/15-minute schedule."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from market_data.models.exceptions import ProviderConnectionError
from market_data.services.lifecycle_scheduler import TreasuryBillLifecycleScheduler
from market_data.services.treasury_bill_sync import (
    A3ActivationResult,
    TreasuryDiscoveryResult,
)

_START = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


class _SyncService:
    def __init__(self, fail_treasury=False):
        self.fail_treasury = fail_treasury
        self.treasury_calls = 0
        self.a3_calls = 0

    def refresh_treasury(self, evaluated_at, max_result_articles=None):
        self.treasury_calls += 1
        if self.fail_treasury:
            raise ProviderConnectionError("official source unavailable")
        return TreasuryDiscoveryResult(
            notices_checked=1,
            candidates_discovered=2,
            decisions=(),
        )

    def refresh_a3(self, evaluated_at):
        self.a3_calls += 1
        return A3ActivationResult(
            quotes_received=3,
            quotes_saved=3,
            candidates_evaluated=2,
            active_for_analysis=1,
            pending_secondary_market=1,
            pending_match=0,
            matured=0,
            decisions=(),
        )


class LifecycleSchedulerTests(unittest.TestCase):
    def test_runs_both_immediately_then_uses_independent_intervals(self):
        service = _SyncService()
        scheduler = TreasuryBillLifecycleScheduler(service)

        first = scheduler.run_due(_START)
        self.assertIsNotNone(first.treasury)
        self.assertIsNotNone(first.a3)
        self.assertEqual(scheduler.seconds_until_next(_START), 900)

        early = scheduler.run_due(_START + timedelta(minutes=14))
        self.assertIsNone(early.treasury)
        self.assertIsNone(early.a3)

        quarter_hour = scheduler.run_due(_START + timedelta(minutes=15))
        self.assertIsNone(quarter_hour.treasury)
        self.assertIsNotNone(quarter_hour.a3)
        self.assertEqual(service.treasury_calls, 1)
        self.assertEqual(service.a3_calls, 2)

        next_day = scheduler.run_due(_START + timedelta(days=1))
        self.assertIsNotNone(next_day.treasury)
        self.assertIsNotNone(next_day.a3)
        self.assertEqual(service.treasury_calls, 2)
        self.assertEqual(service.a3_calls, 3)

    def test_source_failure_does_not_block_other_schedule(self):
        service = _SyncService(fail_treasury=True)
        tick = TreasuryBillLifecycleScheduler(service).run_due(_START)
        self.assertIn("ProviderConnectionError", tick.treasury_error or "")
        self.assertIsNotNone(tick.a3)
        self.assertEqual(service.a3_calls, 1)

    def test_rejects_invalid_intervals_and_naive_timestamps(self):
        with self.assertRaises(ValueError):
            TreasuryBillLifecycleScheduler(_SyncService(), a3_interval_seconds=0)
        scheduler = TreasuryBillLifecycleScheduler(_SyncService())
        with self.assertRaises(ValueError):
            scheduler.run_due(datetime(2026, 8, 10, 12, 0))


if __name__ == "__main__":
    unittest.main()
