"""Tests for the Market Data domain models, enums, config and Protocols.

No network, no storage IO and no financial formulas are involved.
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from market_data.config import A3ApiConfig, MarketDataSettings, ProviderConfig
from market_data.models import (
    ApiEnvironment,
    CurvePoint,
    FxForwardCurve,
    FxForwardPoint,
    InstrumentClass,
    MarketDataError,
    MarketQuote,
    MethodologyStatus,
    PriceType,
    ProviderName,
    SchemaVersionError,
    StorageError,
)
from market_data.providers import MarketDataProvider, QuoteQuery
from market_data.storage import MarketDataRepository


def _sample_quote() -> MarketQuote:
    return MarketQuote(
        ticker="AE38",
        description="AE38 (BONO USD STEP UP 2038 L.A.)",
        issue_type="TPN",
        segment="Bilateral TRD",
        segment_code="BT",
        term="000",
        term_code="000",
        currency="$",
        market_date=date(2024, 11, 15),
        settlement_date=None,
        last_price=Decimal("759.65"),
        close_price=Decimal("759.65"),
        previous_close=Decimal("0"),
        min_price=Decimal("755"),
        max_price=Decimal("759.65"),
        provider_rate=Decimal("0"),
        accumulated_volume=Decimal("14811266"),
        accumulated_amount=Decimal("11235165909"),
        open_interest=Decimal("0"),
        variation=Decimal("0.07"),
        bid=None,
        ask=None,
        instrument_class=InstrumentClass.FIXED_INCOME,
        provider=ProviderName.A3,
        retrieved_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
    )


# --- Enums -----------------------------------------------------------------
def test_price_type_members():
    assert {p.value for p in PriceType} == {"SETTLEMENT", "LAST", "BID", "ASK", "MID"}


def test_methodology_status_members():
    assert {m.value for m in MethodologyStatus} == {
        "PENDING",
        "UNDER_REVIEW",
        "VALIDATED",
    }


def test_instrument_class_has_a3_segments():
    values = {c.value for c in InstrumentClass}
    assert {"FIXED_INCOME", "CAUCION", "FOREX", "REPO"} <= values


def test_api_environment_members():
    assert {e.value for e in ApiEnvironment} == {"UAT", "PROD"}


# --- Immutability & Decimal ------------------------------------------------
def test_quote_is_frozen():
    quote = _sample_quote()
    with pytest.raises(dataclasses.FrozenInstanceError):
        quote.last_price = Decimal("0")  # type: ignore[misc]


def test_quote_prices_are_decimal():
    quote = _sample_quote()
    for value in (quote.last_price, quote.min_price, quote.max_price, quote.variation):
        assert isinstance(value, Decimal)


def test_absent_price_is_none():
    quote = _sample_quote()
    assert quote.bid is None
    assert quote.ask is None
    assert quote.settlement_date is None


# --- Curves (unchanged futures models) -------------------------------------
def test_fx_forward_point_devaluation_gated():
    point = FxForwardPoint(
        ticker="DLR/AGO26",
        maturity_date=date(2026, 8, 31),
        spot=Decimal("1400.00"),
        future_price=Decimal("1450.50"),
        forward_points=Decimal("50.50"),
        implied_devaluation=None,
        methodology_status=MethodologyStatus.UNDER_REVIEW,
    )
    assert point.forward_points == Decimal("50.50")
    assert point.implied_devaluation is None


def test_fx_forward_curve_requires_disclaimer():
    curve = FxForwardCurve(
        valuation_date=date(2026, 8, 6),
        underlying_asset="USD",
        points=(),
        provider=ProviderName.A3,
        futures_as_forward_disclaimer="Futures-as-forward proxy — Under Review (R-009).",
    )
    assert "R-009" in curve.futures_as_forward_disclaimer


def test_curve_point_gated_rate():
    point = CurvePoint(
        ticker="DLR/AGO26",
        maturity_date=date(2026, 8, 31),
        days_to_maturity=25,
        price=Decimal("1450.50"),
        implied_rate=None,
        methodology_status=MethodologyStatus.PENDING,
    )
    assert point.implied_rate is None


# --- Exceptions ------------------------------------------------------------
def test_exception_hierarchy():
    assert issubclass(StorageError, MarketDataError)
    assert issubclass(SchemaVersionError, StorageError)


# --- Config ----------------------------------------------------------------
def test_default_settings_target_fixed_income():
    settings = MarketDataSettings()
    assert isinstance(settings.provider, ProviderConfig)
    assert settings.provider.provider is ProviderName.A3
    assert settings.provider.instrument_classes == (InstrumentClass.FIXED_INCOME,)
    assert settings.a3_update_frequency_seconds == 900
    assert settings.treasury_update_frequency_seconds == 86400


def test_a3_config_base_urls():
    assert (
        A3ApiConfig(environment=ApiEnvironment.UAT).base_url()
        == "https://apiuat.mae.com.ar/MarketData/v1"
    )
    assert (
        A3ApiConfig(environment=ApiEnvironment.PROD).base_url()
        == "https://api.mae.com.ar/MarketData/v1"
    )


def test_a3_config_from_env_selects_environment(monkeypatch):
    monkeypatch.setenv("A3_MARKETDATA_ENV", "PROD")
    assert A3ApiConfig.from_env().environment is ApiEnvironment.PROD
    monkeypatch.setenv("A3_MARKETDATA_ENV", "UAT")
    assert A3ApiConfig.from_env().environment is ApiEnvironment.UAT
    monkeypatch.delenv("A3_MARKETDATA_ENV", raising=False)
    assert A3ApiConfig.from_env().environment is ApiEnvironment.UAT  # default


def test_a3_config_missing_key_raises(monkeypatch):
    from market_data.models.exceptions import ConfigurationError

    monkeypatch.delenv("A3_MARKETDATA_API_KEY_UAT", raising=False)
    with pytest.raises(ConfigurationError):
        A3ApiConfig(environment=ApiEnvironment.UAT).api_key()


# --- Protocols -------------------------------------------------------------
def test_provider_protocol_is_runtime_checkable():
    class _DummyProvider:
        name = ProviderName.MOCK

        def fetch_quotes(self, query):
            return ()

        def health_check(self):
            return True

    assert isinstance(_DummyProvider(), MarketDataProvider)


def test_incomplete_provider_is_not_instance():
    class _Incomplete:
        name = ProviderName.MOCK

    assert not isinstance(_Incomplete(), MarketDataProvider)


def test_quote_query_defaults():
    q = QuoteQuery(instrument_class=InstrumentClass.FIXED_INCOME)
    assert q.segmento is None and q.page_number is None


def test_repository_protocol_is_runtime_checkable():
    class _DummyRepo:
        def initialize(self):
            return None

        def save_quotes(self, quotes):
            return 0

        def get_quotes(self, ticker, start, end, instrument_class=None):
            return ()

        def get_latest_quotes(self, instrument_class):
            return ()

        def get_tickers(self, instrument_class):
            return ()

    assert isinstance(_DummyRepo(), MarketDataRepository)
