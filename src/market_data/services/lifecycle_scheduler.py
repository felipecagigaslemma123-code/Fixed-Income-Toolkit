"""Independent recurring schedule for Treasury discovery and A3 refreshes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from market_data.models.exceptions import MarketDataError
from market_data.services.treasury_bill_sync import (
    A3ActivationResult,
    TreasuryBillSyncService,
    TreasuryDiscoveryResult,
)


@dataclass(frozen=True)
class SchedulerTickResult:
    """Jobs attempted during one non-blocking scheduler tick."""

    treasury: Optional[TreasuryDiscoveryResult]
    treasury_error: Optional[str]
    a3: Optional[A3ActivationResult]
    a3_error: Optional[str]


class TreasuryBillLifecycleScheduler:
    """Run two independent jobs at the owner-approved frequencies.

    The scheduler does not sleep and does not own a process. ``run_due`` can be
    called by a CLI loop, cron wrapper or future service host. Each source is
    attempted immediately on startup. A failure in one source does not prevent
    the other source from running.
    """

    def __init__(
        self,
        sync_service: TreasuryBillSyncService,
        treasury_interval_seconds: int = 86400,
        a3_interval_seconds: int = 900,
        max_result_articles: Optional[int] = None,
    ) -> None:
        if treasury_interval_seconds <= 0 or a3_interval_seconds <= 0:
            raise ValueError("Scheduler intervals must be positive")
        if max_result_articles is not None and max_result_articles < 1:
            raise ValueError("max_result_articles must be at least 1")
        self._sync_service = sync_service
        self._treasury_interval = timedelta(seconds=treasury_interval_seconds)
        self._a3_interval = timedelta(seconds=a3_interval_seconds)
        self._max_result_articles = max_result_articles
        self._last_treasury_attempt: Optional[datetime] = None
        self._last_a3_attempt: Optional[datetime] = None

    @staticmethod
    def _validate_timestamp(now: datetime) -> None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Scheduler timestamps must be timezone-aware")

    @staticmethod
    def _is_due(
        now: datetime,
        previous: Optional[datetime],
        interval: timedelta,
    ) -> bool:
        return previous is None or now - previous >= interval

    @staticmethod
    def _error_text(exc: MarketDataError) -> str:
        return "{}: {}".format(type(exc).__name__, exc)

    def run_due(self, now: datetime) -> SchedulerTickResult:
        """Attempt every job currently due and return without sleeping."""
        self._validate_timestamp(now)
        treasury_result = None
        treasury_error = None
        a3_result = None
        a3_error = None

        if self._is_due(now, self._last_treasury_attempt, self._treasury_interval):
            self._last_treasury_attempt = now
            try:
                treasury_result = self._sync_service.refresh_treasury(
                    evaluated_at=now,
                    max_result_articles=self._max_result_articles,
                )
            except MarketDataError as exc:
                treasury_error = self._error_text(exc)

        if self._is_due(now, self._last_a3_attempt, self._a3_interval):
            self._last_a3_attempt = now
            try:
                a3_result = self._sync_service.refresh_a3(evaluated_at=now)
            except MarketDataError as exc:
                a3_error = self._error_text(exc)

        return SchedulerTickResult(
            treasury=treasury_result,
            treasury_error=treasury_error,
            a3=a3_result,
            a3_error=a3_error,
        )

    def seconds_until_next(self, now: datetime) -> int:
        """Return whole seconds until either source is next due."""
        self._validate_timestamp(now)
        if self._last_treasury_attempt is None or self._last_a3_attempt is None:
            return 0
        treasury_remaining = (
            self._last_treasury_attempt + self._treasury_interval - now
        ).total_seconds()
        a3_remaining = (
            self._last_a3_attempt + self._a3_interval - now
        ).total_seconds()
        return max(0, int(math.ceil(min(treasury_remaining, a3_remaining))))
