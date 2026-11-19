"""Provider-agnostic interface for market data sources.

A provider only needs to satisfy this Protocol shape; it does not import a base
class. Swapping providers (A3/MAE, a future Matba Rofex, CSV, Mock) is therefore
a matter of adding one file, with no changes elsewhere in the Toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Tuple, runtime_checkable

from market_data.models.enums import InstrumentClass, ProviderName
from market_data.models.futures import (
    FuturesContractReference,
    FuturesTradeObservation,
)
from market_data.models.quote import MarketQuote


@dataclass(frozen=True)
class QuoteQuery:
    """Filters for a market-data query.

    Mirrors the A3 / MAE MarketData query parameters. All filters are optional
    except the segment (``instrument_class``).

    Attributes:
        instrument_class: Segment to query (fixed income, forex, ...).
        segmento: Optional segment filter.
        plazo: Optional settlement-term filter.
        moneda: Optional currency filter.
        ticker: Optional ticker filter.
        page_number: Optional pagination index.
    """

    instrument_class: InstrumentClass
    segmento: Optional[str] = None
    plazo: Optional[str] = None
    moneda: Optional[str] = None
    ticker: Optional[str] = None
    page_number: Optional[int] = None


@runtime_checkable
class MarketDataProvider(Protocol):
    """Contract that every market data provider must fulfill.

    Implementations do exactly two things: talk to their source and return
    normalized domain objects. They must not persist, cache, compute financial
    formulas or render anything.
    """

    name: ProviderName

    def fetch_quotes(self, query: QuoteQuery) -> Tuple[MarketQuote, ...]:
        """Fetch normalized quotes for a query.

        Args:
            query: Segment and optional filters.

        Returns:
            The quotes returned by the provider for the query.
        """
        ...

    def health_check(self) -> bool:
        """Report provider availability, for logging and future failover.

        Returns:
            ``True`` if the provider is reachable and responding.
        """
        ...


@runtime_checkable
class FuturesDataProvider(Protocol):
    """Read-only contract for observed futures reference data and trades."""

    name: ProviderName

    def fetch_contracts(self) -> Tuple[FuturesContractReference, ...]:
        """Fetch the currently listed, supported futures contracts."""
        ...

    def fetch_recent_trades(
        self, contract: FuturesContractReference
    ) -> Tuple[FuturesTradeObservation, ...]:
        """Fetch recent observed trades for one contract."""
        ...

    def health_check(self) -> bool:
        """Report whether the public reference-data source responds."""
        ...
