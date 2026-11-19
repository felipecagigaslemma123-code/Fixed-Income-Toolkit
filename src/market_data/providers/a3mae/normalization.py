"""Pure raw-to-domain mapping for the A3 / MAE MarketData API.

No network, no IO. Given the raw JSON body of a quote endpoint, produce a tuple
of :class:`MarketQuote`. Every numeric value becomes a :class:`decimal.Decimal`
via ``str`` (never through ``float``); JSON is parsed with ``parse_float=Decimal``
as a second safeguard.

The API sends ``0001-01-01T00:00:00`` for a non-applicable settlement date; that
is mapped to ``None``.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Tuple

from market_data.models.enums import InstrumentClass, ProviderName
from market_data.models.exceptions import NormalizationError
from market_data.models.quote import MarketQuote

_NA_DATE_PREFIX = "0001-01-01"


def _to_decimal(value: Any) -> Optional[Decimal]:
    """Convert a raw numeric value to Decimal, or ``None`` if absent.

    Uses ``Decimal(str(value))`` so ints and already-Decimal values are exact and
    no binary ``float`` is ever introduced.
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError) as exc:
        raise NormalizationError(
            "Cannot convert value to Decimal: {!r}".format(value)
        ) from exc


def _to_date(value: Any) -> Optional[date]:
    """Convert an ISO date/datetime string to a date, or ``None``.

    Returns ``None`` for empty values and for the API's ``0001-01-01`` sentinel.
    """
    if not value:
        return None
    text = str(value)
    if text.startswith(_NA_DATE_PREFIX):
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise NormalizationError("Cannot parse date: {!r}".format(value)) from exc


def _to_text(value: Any) -> Optional[str]:
    """Return a trimmed string, or ``None`` for empty/absent values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _row_to_quote(
    row: dict,
    instrument_class: InstrumentClass,
    provider: ProviderName,
    retrieved_at: datetime,
) -> MarketQuote:
    """Map one raw API row to a :class:`MarketQuote`."""
    market_date = _to_date(row.get("fecha"))
    if market_date is None:
        raise NormalizationError(
            "Quote is missing a valid 'fecha': {!r}".format(row.get("ticker"))
        )
    return MarketQuote(
        ticker=_to_text(row.get("ticker")) or "",
        description=_to_text(row.get("descripcion")),
        issue_type=_to_text(row.get("tipoEmision")),
        segment=_to_text(row.get("segmento")),
        segment_code=_to_text(row.get("codigoSegmento")),
        term=_to_text(row.get("plazo")),
        term_code=_to_text(row.get("codigoPlazo")),
        currency=_to_text(row.get("moneda")),
        market_date=market_date,
        settlement_date=_to_date(row.get("fechaLiquidacion")),
        last_price=_to_decimal(row.get("precioUltimo")),
        close_price=_to_decimal(row.get("precioCierre")),
        previous_close=_to_decimal(row.get("precioCierreAnterior")),
        min_price=_to_decimal(row.get("precioMinimo")),
        max_price=_to_decimal(row.get("precioMaximo")),
        provider_rate=_to_decimal(row.get("ultimaTasa")),
        accumulated_volume=_to_decimal(row.get("volumenAcumulado")),
        accumulated_amount=_to_decimal(row.get("montoAcumulado")),
        open_interest=_to_decimal(row.get("openInterest")),
        variation=_to_decimal(row.get("variacion")),
        bid=_to_decimal(row.get("bid")),  # not published by A3 cash segments
        ask=_to_decimal(row.get("ask")),
        instrument_class=instrument_class,
        provider=provider,
        retrieved_at=retrieved_at,
    )


def parse_quotes(
    raw_body: str,
    instrument_class: InstrumentClass,
    provider: ProviderName,
    retrieved_at: datetime,
) -> Tuple[MarketQuote, ...]:
    """Parse the raw JSON body of a quote endpoint into domain quotes.

    Args:
        raw_body: The JSON response body (a list of quote objects).
        instrument_class: Segment the quotes belong to.
        provider: Provider that supplied the data.
        retrieved_at: Reception timestamp (UTC).

    Returns:
        The parsed quotes, in the order returned by the provider.

    Raises:
        NormalizationError: If the body is not valid JSON, is not a list, or a
            row cannot be mapped.
    """
    try:
        data = json.loads(raw_body, parse_float=Decimal)
    except json.JSONDecodeError as exc:
        raise NormalizationError("Response body is not valid JSON") from exc
    if not isinstance(data, list):
        raise NormalizationError(
            "Expected a JSON list of quotes, got {}".format(type(data).__name__)
        )
    return tuple(
        _row_to_quote(row, instrument_class, provider, retrieved_at) for row in data
    )
