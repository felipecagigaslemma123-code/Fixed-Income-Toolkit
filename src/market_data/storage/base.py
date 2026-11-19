"""Storage-agnostic repository interface for the Market Data layer.

The repository persists and queries :class:`MarketQuote` rows. It never talks to
providers or the network, and never computes financial formulas. Keeping this as
a Protocol lets the SQLite implementation be swapped (e.g. for PostgreSQL)
without touching services or the public API.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol, Sequence, Tuple, runtime_checkable

from market_data.models.enums import InstrumentClass
from market_data.models.quote import MarketQuote


@runtime_checkable
class MarketDataRepository(Protocol):
    """Contract that every persistence backend must fulfill."""

    def initialize(self) -> None:
        """Create the schema if it does not exist (idempotent)."""
        ...

    def save_quotes(self, quotes: Sequence[MarketQuote]) -> int:
        """Persist quotes.

        One row per natural key (ticker, instrument class, term, market date,
        provider); re-saving the same key updates it with the newer observation,
        so history accumulates across market dates without duplicates.

        Args:
            quotes: Quotes to persist.

        Returns:
            The number of quotes written.
        """
        ...

    def get_quotes(
        self,
        ticker: str,
        start: date,
        end: date,
        instrument_class: Optional[InstrumentClass] = None,
    ) -> Tuple[MarketQuote, ...]:
        """Return stored quotes for a ticker within a market-date range."""
        ...

    def get_latest_quotes(
        self, instrument_class: InstrumentClass
    ) -> Tuple[MarketQuote, ...]:
        """Return the most recent quote per ticker for a segment."""
        ...

    def get_tickers(self, instrument_class: InstrumentClass) -> Tuple[str, ...]:
        """Return the distinct tickers stored for a segment."""
        ...
