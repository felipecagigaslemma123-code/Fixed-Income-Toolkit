"""Orchestration for provisional public dollar-futures observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from market_data.models.exceptions import MarketDataError, ProviderResponseError
from market_data.providers.base import FuturesDataProvider
from market_data.storage.futures_repository import SqliteFuturesRepository


@dataclass(frozen=True)
class FuturesContractSyncResult:
    """Outcome of one complete reference-data refresh."""

    contracts_received: int
    contracts_saved: int


@dataclass(frozen=True)
class FuturesTradeSyncResult:
    """Outcome of one recent-trade refresh across active contracts."""

    contracts_attempted: int
    contracts_failed: Tuple[str, ...]
    trades_received: int
    trades_saved: int


class FuturesSyncService:
    """Keep provider IO and SQLite persistence separate from presentation."""

    def __init__(
        self,
        provider: FuturesDataProvider,
        repository: SqliteFuturesRepository,
    ) -> None:
        self._provider = provider
        self._repository = repository

    def refresh_contracts(self) -> FuturesContractSyncResult:
        """Refresh the complete DLR listing without inventing expiry dates."""
        contracts = self._provider.fetch_contracts()
        if not contracts:
            raise ProviderResponseError(
                "Public futures viewer returned no supported DLR contracts; "
                "the existing listing was retained."
            )
        saved = self._repository.save_contract_snapshot(contracts)
        return FuturesContractSyncResult(
            contracts_received=len(contracts), contracts_saved=saved
        )

    def refresh_trades(self) -> FuturesTradeSyncResult:
        """Refresh each active contract independently and keep partial success."""
        contracts = self._repository.get_contracts(active_only=True)
        if not contracts:
            self.refresh_contracts()
            contracts = self._repository.get_contracts(active_only=True)

        received = 0
        saved = 0
        failed = []
        for contract in contracts:
            try:
                trades = self._provider.fetch_recent_trades(contract)
                received += len(trades)
                saved += self._repository.save_trades(trades)
            except MarketDataError:
                failed.append(contract.ticker)
        return FuturesTradeSyncResult(
            contracts_attempted=len(contracts),
            contracts_failed=tuple(failed),
            trades_received=received,
            trades_saved=saved,
        )
