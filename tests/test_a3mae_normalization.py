"""Tests for the A3 / MAE MarketData normalizer.

Fixtures are the real example payloads captured from the official Swagger
(``docs/providers/a3_provider_contract.md``). Pure, offline, deterministic.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from market_data.models.enums import InstrumentClass, ProviderName
from market_data.models.exceptions import NormalizationError
from market_data.providers.a3mae.normalization import parse_quotes

_RETRIEVED_AT = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)

# Real example row for Renta Fija (settlement date not applicable -> 0001-01-01).
_RENTAFIJA_JSON = """
[
  {
    "fecha": "2024-11-15T00:00:00",
    "ticker": "AE38",
    "descripcion": "AE38  (BONO USD STEP UP 2038 L.A.)",
    "tipoEmision": "TPN",
    "segmento": "Bilateral TRD",
    "codigoSegmento": "BT",
    "plazo": "000",
    "codigoPlazo": "000",
    "moneda": "$",
    "fechaLiquidacion": "0001-01-01T00:00:00",
    "volumenAcumulado": 14811266,
    "montoAcumulado": 11235165909,
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

# Real example row for Cauciones (real settlement date; nulls present).
_CAUCIONES_JSON = """
[
  {
    "fecha": "2024-11-25T00:00:00",
    "ticker": "CAARS",
    "descripcion": "CAARS $ 001",
    "tipoEmision": "CAU",
    "segmento": null,
    "codigoSegmento": "K",
    "plazo": "001",
    "codigoPlazo": null,
    "moneda": "$",
    "fechaLiquidacion": "2024-11-26T00:00:00",
    "volumenAcumulado": 1611021618572,
    "montoAcumulado": 0,
    "precioUltimo": 0,
    "ultimaTasa": 32.9,
    "precioCierreAnterior": 0,
    "precioMinimo": 0,
    "precioMaximo": 0,
    "openInterest": 0,
    "precioCierre": null,
    "variacion": 0
  }
]
"""


def test_rentafija_row_maps_all_fields():
    quotes = parse_quotes(
        _RENTAFIJA_JSON, InstrumentClass.FIXED_INCOME, ProviderName.A3, _RETRIEVED_AT
    )
    assert len(quotes) == 1
    q = quotes[0]
    assert q.ticker == "AE38"
    assert q.description == "AE38  (BONO USD STEP UP 2038 L.A.)"
    assert q.issue_type == "TPN"
    assert q.segment == "Bilateral TRD"
    assert q.segment_code == "BT"
    assert q.term == "000"
    assert q.currency == "$"
    assert q.market_date == date(2024, 11, 15)
    assert q.settlement_date is None  # 0001-01-01 sentinel -> None
    assert q.last_price == Decimal("759.65")
    assert q.close_price == Decimal("759.65")
    assert q.min_price == Decimal("755")
    assert q.max_price == Decimal("759.65")
    assert q.accumulated_volume == Decimal("14811266")
    assert q.variation == Decimal("0.07")
    assert q.bid is None and q.ask is None
    assert q.instrument_class is InstrumentClass.FIXED_INCOME
    assert q.provider is ProviderName.A3
    assert q.retrieved_at == _RETRIEVED_AT


def test_prices_are_decimal_never_float():
    quotes = parse_quotes(
        _RENTAFIJA_JSON, InstrumentClass.FIXED_INCOME, ProviderName.A3, _RETRIEVED_AT
    )
    q = quotes[0]
    for value in (
        q.last_price,
        q.close_price,
        q.previous_close,
        q.min_price,
        q.max_price,
        q.provider_rate,
        q.accumulated_volume,
        q.accumulated_amount,
        q.open_interest,
        q.variation,
    ):
        assert value is None or isinstance(value, Decimal)
        assert not isinstance(value, float)


def test_cauciones_nulls_and_settlement_date():
    quotes = parse_quotes(
        _CAUCIONES_JSON, InstrumentClass.CAUCION, ProviderName.A3, _RETRIEVED_AT
    )
    q = quotes[0]
    assert q.segment is None  # null -> None
    assert q.term_code is None  # null -> None
    assert q.close_price is None  # null -> None
    assert q.provider_rate == Decimal("32.9")  # raw provider rate, stored as-is
    assert q.settlement_date == date(2024, 11, 26)
    assert q.instrument_class is InstrumentClass.CAUCION


def test_invalid_json_raises():
    with pytest.raises(NormalizationError):
        parse_quotes("{not json", InstrumentClass.FIXED_INCOME, ProviderName.A3, _RETRIEVED_AT)


def test_non_list_body_raises():
    with pytest.raises(NormalizationError):
        parse_quotes('{"a": 1}', InstrumentClass.FIXED_INCOME, ProviderName.A3, _RETRIEVED_AT)


def test_empty_list_yields_no_quotes():
    assert parse_quotes("[]", InstrumentClass.FIXED_INCOME, ProviderName.A3, _RETRIEVED_AT) == ()
