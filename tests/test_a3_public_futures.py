"""Offline tests for the provisional public futures provider."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from market_data.config import A3PublicFuturesConfig
from market_data.models import FuturesContractReference, ProviderName
from market_data.models.exceptions import NormalizationError
from market_data.providers import FuturesDataProvider
from market_data.providers.a3_public_futures import A3PublicFuturesProvider
from market_data.providers.a3_public_futures.normalization import (
    parse_contracts,
    parse_trades,
)

_NOW = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)

_REFERENCE_BODY = """[
  {
    "id": "rx_DDF_DLR_AGO26",
    "symbol": "DLR/AGO26",
    "description": "Futuro de Dólar Agosto 2026",
    "cfiCode": "FXXXSX",
    "marketId": "ROFX",
    "marketSegmentId": "DDF",
    "currency": "ARS",
    "maturityMonthYear": "202608",
    "endDate": "2026-08-10",
    "daysToExpiration": 21,
    "contractMultiplier": 1000,
    "pricePrecision": 1,
    "sizePrecision": 0,
    "minPriceIncrement": 0.5000,
    "settlementType": "Cash",
    "underlying": "USD",
    "underlyingSymbol": "DLR"
  },
  {
    "id": "rx_DDF_DLR_AGO26M",
    "symbol": "DLR/AGO26M",
    "description": "Mini Futuro de Dólar Agosto 2026",
    "cfiCode": "FXXXSX",
    "daysToExpiration": 21,
    "contractMultiplier": "100",
    "minPriceIncrement": "0.5"
  },
  {"id": "option", "symbol": "DLR/AGO26 1500 C", "cfiCode": "OCASPS"},
  {"id": "other", "symbol": "SOJ/NOV26", "cfiCode": "FXXXSX"}
]"""

_TRADE_BODY = """{
  "trades": [
    {
      "id": 987654,
      "timestamp": "2026-08-10T17:32:10.123Z",
      "type": "Trade",
      "price": 1509.5000,
      "sides": ["Buy", "Sell"],
      "volume": 2,
      "securityId": "rx_DDF_DLR_AGO26",
      "sellerParty": "A",
      "buyerParty": "B"
    }
  ]
}"""


def test_reference_filter_and_decimal_integrity():
    contracts = parse_contracts(_REFERENCE_BODY, _NOW)
    assert [contract.ticker for contract in contracts] == [
        "DLR/AGO26",
        "DLR/AGO26M",
    ]
    standard, mini = contracts
    assert standard.contract_multiplier == Decimal("1000")
    assert standard.min_price_increment == Decimal("0.5000")
    assert standard.source_end_date == "2026-08-10"
    assert standard.days_to_expiration == 21
    assert not standard.is_mini
    assert mini.is_mini


def test_trade_price_is_decimal_and_timestamp_is_preserved():
    contract = parse_contracts(_REFERENCE_BODY, _NOW)[0]
    trade = parse_trades(_TRADE_BODY, contract, _NOW)[0]
    assert trade.price == Decimal("1509.5000")
    assert trade.volume == Decimal("2")
    assert trade.provider_timestamp == "2026-08-10T17:32:10.123Z"
    assert trade.provider_timezone == "UTC"
    assert trade.timestamp_utc == datetime(
        2026, 8, 10, 17, 32, 10, 123000, tzinfo=timezone.utc
    )
    assert trade.provider is ProviderName.A3_PUBLIC_VIEWER
    assert trade.side_codes == ("Buy", "Sell")


def test_trade_rejects_an_ambiguous_naive_timestamp():
    contract = parse_contracts(_REFERENCE_BODY, _NOW)[0]
    body = _TRADE_BODY.replace("2026-08-10T17:32:10.123Z", "2026-08-10T17:32:10")
    with pytest.raises(NormalizationError):
        parse_trades(body, contract, _NOW)


def test_provider_uses_read_only_public_routes_and_protocol():
    calls = []

    def transport(url, headers, timeout):
        calls.append((url, headers, timeout))
        return _REFERENCE_BODY if url.endswith("/ref-data") else _TRADE_BODY

    provider = A3PublicFuturesProvider(
        A3PublicFuturesConfig(base_url="https://viewer.example/api/v2"),
        transport=transport,
    )
    assert isinstance(provider, FuturesDataProvider)
    contracts = provider.fetch_contracts()
    trades = provider.fetch_recent_trades(contracts[0])
    assert len(trades) == 1
    assert calls[0][0] == "https://viewer.example/api/v2/ref-data"
    assert calls[1][0].endswith("/trades/securities/rx_DDF_DLR_AGO26")
    assert "x-api-key" not in {key.lower() for key in calls[0][1]}


def test_reference_model_does_not_claim_an_exact_maturity_date():
    fields = FuturesContractReference.__dataclass_fields__
    assert "maturity_date" not in fields
    assert "source_end_date" in fields
