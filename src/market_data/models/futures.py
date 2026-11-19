"""Observed dollar-futures reference and trade models.

These immutable models contain provider observations only. They deliberately do
not contain spot, forward points, implied rates or any other R-009 calculation.
Every financial magnitude uses :class:`decimal.Decimal`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

from market_data.models.enums import ProviderName


@dataclass(frozen=True)
class FuturesContractReference:
    """Reference fields supplied for one listed futures contract.

    ``source_end_date`` preserves the provider field without asserting that it
    is the contractual expiry date. The public viewer does not expose enough
    evidence to map that field safely to ``maturity_date``.
    """

    security_id: str
    ticker: str
    description: Optional[str]
    cfi_code: str
    market_id: Optional[str]
    market_segment_id: Optional[str]
    currency: Optional[str]
    maturity_month_year: Optional[str]
    source_end_date: Optional[str]
    days_to_expiration: Optional[int]
    contract_multiplier: Optional[Decimal]
    price_precision: Optional[int]
    size_precision: Optional[int]
    min_price_increment: Optional[Decimal]
    settlement_type: Optional[str]
    underlying_id: Optional[str]
    underlying_symbol: Optional[str]
    retrieved_at: datetime
    is_active: bool = True
    first_seen_at: Optional[datetime] = None

    @property
    def is_mini(self) -> bool:
        """Return the market-symbol classification, without a calculation."""
        return self.ticker.endswith("M")


@dataclass(frozen=True)
class FuturesTradeObservation:
    """One recent trade returned by the public futures viewer."""

    trade_id: str
    security_id: str
    ticker: str
    provider_timestamp: str
    provider_timezone: str
    timestamp_utc: datetime
    price: Optional[Decimal]
    volume: Optional[Decimal]
    trade_type: Optional[str]
    side_codes: Tuple[str, ...]
    seller_party: Optional[str]
    buyer_party: Optional[str]
    provider: ProviderName
    received_at: datetime
