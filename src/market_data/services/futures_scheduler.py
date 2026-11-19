"""Independent daily-reference and 15-minute-trade futures schedule."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from market_data.models.exceptions import MarketDataError
from market_data.services.futures_sync import (
    FuturesContractSyncResult,
    FuturesSyncService,
    FuturesTradeSyncResult,
)


@dataclass(frozen=True)
class FuturesSchedulerTickResult:
    """Jobs attempted during one non-blocking futures scheduler tick."""

    contracts: Optional[FuturesContractSyncResult]
    contracts_error: Optional[str]
    trades: Optional[FuturesTradeSyncResult]
    trades_error: Optional[str]


class FuturesScheduler:
    """Run public reference and recent-trade jobs at separate frequencies."""

    def __init__(
        self,
        sync_service: FuturesSyncService,
        contract_interval_seconds: int = 86400,
        trade_interval_seconds: int = 900,
    ) -> None:
        if contract_interval_seconds <= 0 or trade_interval_seconds <= 0:
            raise ValueError("Scheduler intervals must be positive")
        self._sync_service = sync_service
        self._contract_interval = timedelta(seconds=contract_interval_seconds)
        self._trade_interval = timedelta(seconds=trade_interval_seconds)
        self._last_contract_attempt: Optional[datetime] = None
        self._last_trade_attempt: Optional[datetime] = None

    @staticmethod
    def _validate_timestamp(now: datetime) -> None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Scheduler timestamps must be timezone-aware")

    @staticmethod
    def _due(
        now: datetime, previous: Optional[datetime], interval: timedelta
    ) -> bool:
        return previous is None or now - previous >= interval

    @staticmethod
    def _error(exc: MarketDataError) -> str:
        return "{}: {}".format(type(exc).__name__, exc)

    def run_due(self, now: datetime) -> FuturesSchedulerTickResult:
        """Attempt every due job, keeping one source failure isolated."""
        self._validate_timestamp(now)
        contracts = None
        contracts_error = None
        trades = None
        trades_error = None

        if self._due(now, self._last_contract_attempt, self._contract_interval):
            self._last_contract_attempt = now
            try:
                contracts = self._sync_service.refresh_contracts()
            except MarketDataError as exc:
                contracts_error = self._error(exc)

        if self._due(now, self._last_trade_attempt, self._trade_interval):
            self._last_trade_attempt = now
            try:
                trades = self._sync_service.refresh_trades()
            except MarketDataError as exc:
                trades_error = self._error(exc)

        return FuturesSchedulerTickResult(
            contracts=contracts,
            contracts_error=contracts_error,
            trades=trades,
            trades_error=trades_error,
        )

    def seconds_until_next(self, now: datetime) -> int:
        """Return whole seconds until either source is next due."""
        self._validate_timestamp(now)
        if self._last_contract_attempt is None or self._last_trade_attempt is None:
            return 0
        contract_remaining = (
            self._last_contract_attempt + self._contract_interval - now
        ).total_seconds()
        trade_remaining = (
            self._last_trade_attempt + self._trade_interval - now
        ).total_seconds()
        return max(0, int(math.ceil(min(contract_remaining, trade_remaining))))
