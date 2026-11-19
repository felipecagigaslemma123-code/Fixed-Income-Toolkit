"""Decimal-safe futures repository tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from market_data.models.enums import ProviderName
from market_data.models.futures import (
    FuturesContractReference,
    FuturesTradeObservation,
)
from market_data.storage.futures_repository import SqliteFuturesRepository

_NOW = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)


def _contract(ticker="DLR/AGO26", security_id="rx_DDF_DLR_AGO26", days=21):
    return FuturesContractReference(
        security_id=security_id,
        ticker=ticker,
        description="Dólar futuro",
        cfi_code="FXXXSX",
        market_id="ROFX",
        market_segment_id="DDF",
        currency="ARS",
        maturity_month_year="202608",
        source_end_date="2026-08-10",
        days_to_expiration=days,
        contract_multiplier=Decimal("1000.000"),
        price_precision=1,
        size_precision=0,
        min_price_increment=Decimal("0.5000"),
        settlement_type="Cash",
        underlying_id="USD",
        underlying_symbol="DLR",
        retrieved_at=_NOW,
    )


def _trade(trade_id="1", price="1509.5000", received_at=_NOW):
    return FuturesTradeObservation(
        trade_id=trade_id,
        security_id="rx_DDF_DLR_AGO26",
        ticker="DLR/AGO26",
        provider_timestamp="2026-08-10T17:32:10.123Z",
        provider_timezone="UTC",
        timestamp_utc=datetime(
            2026, 8, 10, 17, 32, 10, 123000, tzinfo=timezone.utc
        ),
        price=Decimal(price),
        volume=Decimal("2.00"),
        trade_type="Trade",
        side_codes=("Buy", "Sell"),
        seller_party="A",
        buyer_party="B",
        provider=ProviderName.A3_PUBLIC_VIEWER,
        received_at=received_at,
    )


def test_contract_and_trade_round_trip_preserves_decimal_text(tmp_path):
    repository = SqliteFuturesRepository(str(tmp_path / "market.sqlite"))
    repository.initialize()
    assert repository.save_contract_snapshot([_contract()]) == 1
    contract = repository.get_contracts()[0]
    assert contract.contract_multiplier == Decimal("1000.000")
    assert contract.min_price_increment == Decimal("0.5000")
    assert contract.first_seen_at == _NOW

    assert repository.save_trades([_trade()]) == 1
    trade = repository.get_latest_trade(contract.security_id)
    assert trade is not None
    assert trade.price == Decimal("1509.5000")
    assert trade.volume == Decimal("2.00")
    assert trade.side_codes == ("Buy", "Sell")
    repository.close()


def test_duplicate_trade_is_idempotent(tmp_path):
    repository = SqliteFuturesRepository(str(tmp_path / "market.sqlite"))
    repository.initialize()
    repository.save_contract_snapshot([_contract()])
    assert repository.save_trades([_trade()]) == 1
    assert repository.save_trades([_trade()]) == 0
    assert repository.trade_count() == 1
    repository.close()


def test_nonempty_snapshot_deactivates_absent_contract_but_empty_does_not(tmp_path):
    repository = SqliteFuturesRepository(str(tmp_path / "market.sqlite"))
    repository.initialize()
    september = _contract("DLR/SEP26", "rx_DDF_DLR_SEP26", 51)
    repository.save_contract_snapshot([_contract(), september])
    assert len(repository.get_contracts()) == 2

    later = replace(_contract(), retrieved_at=_NOW + timedelta(days=1))
    repository.save_contract_snapshot([later])
    assert [item.ticker for item in repository.get_contracts()] == ["DLR/AGO26"]
    assert len(repository.get_contracts(active_only=False)) == 2

    assert repository.save_contract_snapshot([]) == 0
    assert [item.ticker for item in repository.get_contracts()] == ["DLR/AGO26"]
    repository.close()
