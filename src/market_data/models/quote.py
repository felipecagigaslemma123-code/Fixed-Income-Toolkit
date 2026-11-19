"""Market quote and daily snapshot models.

The quote is provider-agnostic but its field set matches the reality of the
A3 / MAE MarketData API (confirmed via Swagger, ``docs/providers/a3_provider_contract.md``):
one unified row for fixed income, cauciones and forex. Prices absent from a
provider are ``None`` (an explicit gap), never a silent substitution. Every
monetary/price magnitude is a :class:`decimal.Decimal` — never ``float``.

``bid``/``ask`` are kept optional for future venues (e.g. futures) that publish
market depth; the A3 cash segments do not provide them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Tuple

from market_data.models.enums import InstrumentClass, Market, ProviderName


@dataclass(frozen=True)
class MarketQuote:
    """A single observation for one instrument.

    Field names map to the A3 / MAE MarketData response (Spanish source field in
    parentheses).

    Attributes:
        ticker: Instrument ticker (``ticker``).
        description: Human-readable description (``descripcion``).
        issue_type: Issue/segment type code, e.g. ``TPN``/``CAU``/``FOR``
            (``tipoEmision``).
        segment: Segment name, e.g. ``Bilateral TRD`` (``segmento``).
        segment_code: Segment code, e.g. ``BT`` (``codigoSegmento``).
        term: Settlement term, e.g. ``000``/``001`` (``plazo``).
        term_code: Term code (``codigoPlazo``).
        currency: Quote currency, e.g. ``$`` (``moneda``).
        market_date: Observation/market date (``fecha``).
        settlement_date: Settlement date, or ``None`` when not applicable
            (``fechaLiquidacion``; the API sends ``0001-01-01`` for N/A).
        last_price: Last traded price (``precioUltimo``).
        close_price: Close price (``precioCierre``).
        previous_close: Previous close (``precioCierreAnterior``).
        min_price: Minimum price (``precioMinimo``).
        max_price: Maximum price (``precioMaximo``).
        provider_rate: Provider-published rate — RAW market data, not a
            Toolkit-calculated yield (``ultimaTasa``).
        accumulated_volume: Accumulated volume (``volumenAcumulado``).
        accumulated_amount: Accumulated amount (``montoAcumulado``).
        open_interest: Open interest (``openInterest``).
        variation: Published change (``variacion``).
        bid: Best bid, if the venue publishes depth (``None`` for A3 cash).
        ask: Best ask, if the venue publishes depth (``None`` for A3 cash).
        instrument_class: Segment this quote belongs to.
        provider: Provider that supplied the observation.
        retrieved_at: Moment the module received the observation (UTC).
    """

    ticker: str
    description: Optional[str]
    issue_type: Optional[str]
    segment: Optional[str]
    segment_code: Optional[str]
    term: Optional[str]
    term_code: Optional[str]
    currency: Optional[str]
    market_date: date
    settlement_date: Optional[date]
    last_price: Optional[Decimal]
    close_price: Optional[Decimal]
    previous_close: Optional[Decimal]
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    provider_rate: Optional[Decimal]
    accumulated_volume: Optional[Decimal]
    accumulated_amount: Optional[Decimal]
    open_interest: Optional[Decimal]
    variation: Optional[Decimal]
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    instrument_class: InstrumentClass
    provider: ProviderName
    retrieved_at: datetime


@dataclass(frozen=True)
class DailySnapshot:
    """An immutable set of quotes for one segment on one market date."""

    snapshot_date: date
    market: Market
    instrument_class: InstrumentClass
    quotes: Tuple[MarketQuote, ...]
    provider: ProviderName
