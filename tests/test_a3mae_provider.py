"""Tests for the A3MaeProvider using an injected fake transport (no network)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from market_data.config.settings import A3ApiConfig
from market_data.models.enums import ApiEnvironment, InstrumentClass, ProviderName
from market_data.models.exceptions import (
    ConfigurationError,
    ProviderAuthError,
    ProviderError,
)
from market_data.providers.a3mae.provider import A3MaeProvider
from market_data.providers.base import MarketDataProvider, QuoteQuery

_FIXTURE = """
[
  {
    "fecha": "2024-11-15T00:00:00",
    "ticker": "AE38",
    "descripcion": "AE38 (BONO USD STEP UP 2038 L.A.)",
    "tipoEmision": "TPN",
    "segmento": "Bilateral TRD",
    "codigoSegmento": "BT",
    "plazo": "001",
    "codigoPlazo": "001",
    "moneda": "$",
    "fechaLiquidacion": "0001-01-01T00:00:00",
    "volumenAcumulado": 100,
    "montoAcumulado": 200,
    "precioUltimo": 759.65,
    "ultimaTasa": 0,
    "precioCierreAnterior": 0,
    "precioMinimo": 755,
    "precioMaximo": 759.65,
    "openInterest": 0,
    "precioCierre": 759.65,
    "variacion": 0.07
  }
]
"""


class _RecordingTransport:
    """Fake transport that records the call and returns a fixed body."""

    def __init__(self, body=_FIXTURE):
        self.body = body
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        return self.body


@pytest.fixture
def uat_config():
    return A3ApiConfig(environment=ApiEnvironment.UAT)


def test_provider_satisfies_protocol(uat_config):
    provider = A3MaeProvider(uat_config, transport=_RecordingTransport())
    assert isinstance(provider, MarketDataProvider)
    assert provider.name is ProviderName.A3


def test_fetch_quotes_builds_url_and_sends_key(monkeypatch, uat_config):
    monkeypatch.setenv("A3_MARKETDATA_API_KEY_UAT", "testkey")
    transport = _RecordingTransport()
    provider = A3MaeProvider(uat_config, transport=transport)

    quotes = provider.fetch_quotes(
        QuoteQuery(instrument_class=InstrumentClass.FIXED_INCOME, plazo="001")
    )

    assert len(quotes) == 1
    assert quotes[0].ticker == "AE38"
    assert quotes[0].last_price == Decimal("759.65")

    call = transport.calls[0]
    assert call["url"].startswith(
        "https://apiuat.mae.com.ar/MarketData/v1/mercado/cotizaciones/rentafija"
    )
    assert "plazo=001" in call["url"]
    assert call["headers"]["x-api-key"] == "testkey"


def test_missing_api_key_raises_configuration_error(monkeypatch, uat_config):
    monkeypatch.delenv("A3_MARKETDATA_API_KEY_UAT", raising=False)
    provider = A3MaeProvider(uat_config, transport=_RecordingTransport())
    with pytest.raises(ConfigurationError):
        provider.fetch_quotes(QuoteQuery(instrument_class=InstrumentClass.FIXED_INCOME))


def test_unsupported_instrument_class_raises(monkeypatch, uat_config):
    monkeypatch.setenv("A3_MARKETDATA_API_KEY_UAT", "testkey")
    provider = A3MaeProvider(uat_config, transport=_RecordingTransport())
    with pytest.raises(ProviderError):
        provider.fetch_quotes(QuoteQuery(instrument_class=InstrumentClass.FX_FUTURE))


def test_auth_error_propagates(monkeypatch, uat_config):
    monkeypatch.setenv("A3_MARKETDATA_API_KEY_UAT", "badkey")

    def failing_transport(url, headers, timeout):
        raise ProviderAuthError("HTTP 401")

    provider = A3MaeProvider(uat_config, transport=failing_transport)
    with pytest.raises(ProviderAuthError):
        provider.fetch_quotes(QuoteQuery(instrument_class=InstrumentClass.FIXED_INCOME))


def test_health_check_true_and_false(monkeypatch, uat_config):
    monkeypatch.setenv("A3_MARKETDATA_API_KEY_UAT", "testkey")
    ok_provider = A3MaeProvider(uat_config, transport=_RecordingTransport())
    assert ok_provider.health_check() is True

    def failing_transport(url, headers, timeout):
        raise ProviderAuthError("HTTP 401")

    bad_provider = A3MaeProvider(uat_config, transport=failing_transport)
    assert bad_provider.health_check() is False


def test_prod_base_url(monkeypatch):
    monkeypatch.setenv("A3_MARKETDATA_API_KEY_PROD", "prodkey")
    config = A3ApiConfig(environment=ApiEnvironment.PROD)
    transport = _RecordingTransport()
    provider = A3MaeProvider(config, transport=transport)
    provider.fetch_quotes(QuoteQuery(instrument_class=InstrumentClass.FOREX))
    assert transport.calls[0]["url"].startswith(
        "https://api.mae.com.ar/MarketData/v1/mercado/cotizaciones/forex"
    )
    assert transport.calls[0]["headers"]["x-api-key"] == "prodkey"
