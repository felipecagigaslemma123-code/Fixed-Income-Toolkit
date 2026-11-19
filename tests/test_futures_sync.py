"""Sync and scheduling tests for observed futures data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from market_data.models.enums import ProviderName
from market_data.models.exceptions import ProviderConnectionError
from market_data.models.futures import (
    FuturesContractReference,
    FuturesTradeObservation,
)
from market_data.services.futures_scheduler import FuturesScheduler
from market_data.services.futures_sync import FuturesSyncService
from market_data.storage.futures_repository import SqliteFuturesRepository

_NOW = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)


def _contract(ticker, security_id, days):
    return FuturesContractReference(
        security_id=security_id,
        ticker=ticker,
        description=None,
        cfi_code="FXXXSX",
        market_id="ROFX",
        market_segment_id="DDF",
        currency="ARS",
        maturity_month_year="202608",
        source_end_date=None,
        days_to_expiration=days,
        contract_multiplier=Decimal("1000"),
        price_precision=1,
        size_precision=0,
        min_price_increment=Decimal("0.5"),
        settlement_type=None,
        underlying_id="USD",
        underlying_symbol="DLR",
        retrieved_at=_NOW,
    )


def _trade(contract):
    return FuturesTradeObservation(
        trade_id="trade-{}".format(contract.ticker),
        security_id=contract.security_id,
        ticker=contract.ticker,
        provider_timestamp="2026-08-10T17:00:00Z",
        provider_timezone="UTC",
        timestamp_utc=datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc),
        price=Decimal("1509.5"),
        volume=Decimal("2"),
        trade_type="Trade",
        side_codes=(),
        seller_party=None,
        buyer_party=None,
        provider=ProviderName.A3_PUBLIC_VIEWER,
        received_at=_NOW,
    )


class _Provider:
    name = ProviderName.A3_PUBLIC_VIEWER

    def __init__(self):
        self.contract_calls = 0
        self.trade_calls = 0
        self.contracts = (
            _contract("DLR/AGO26", "ago", 21),
            _contract("DLR/AGO26M", "agom", 21),
        )

    def fetch_contracts(self):
        self.contract_calls += 1
        return self.contracts

    def fetch_recent_trades(self, contract):
        self.trade_calls += 1
        if contract.ticker.endswith("M"):
            raise ProviderConnectionError("temporary")
        return (_trade(contract),)

    def health_check(self):
        return True


def test_sync_retains_partial_trade_success(tmp_path):
    repository = SqliteFuturesRepository(str(tmp_path / "market.sqlite"))
    repository.initialize()
    provider = _Provider()
    service = FuturesSyncService(provider, repository)
    assert service.refresh_contracts().contracts_saved == 2
    result = service.refresh_trades()
    assert result.contracts_attempted == 2
    assert result.contracts_failed == ("DLR/AGO26M",)
    assert result.trades_received == 1
    assert result.trades_saved == 1
    assert repository.trade_count() == 1
    repository.close()


def test_scheduler_runs_reference_daily_and_trades_every_fifteen_minutes(tmp_path):
    repository = SqliteFuturesRepository(str(tmp_path / "market.sqlite"))
    repository.initialize()
    provider = _Provider()
    scheduler = FuturesScheduler(FuturesSyncService(provider, repository))

    first = scheduler.run_due(_NOW)
    assert first.contracts is not None and first.trades is not None
    assert provider.contract_calls == 1
    assert provider.trade_calls == 2

    scheduler.run_due(_NOW + timedelta(minutes=14))
    assert provider.trade_calls == 2
    scheduler.run_due(_NOW + timedelta(minutes=15))
    assert provider.contract_calls == 1
    assert provider.trade_calls == 4
    scheduler.run_due(_NOW + timedelta(days=1))
    assert provider.contract_calls == 2
    repository.close()
