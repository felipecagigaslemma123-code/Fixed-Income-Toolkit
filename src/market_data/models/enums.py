"""Closed-domain enumerations for the Market Data layer.

Every closed set of domain values is modeled as an ``Enum`` following the
project ``financial_specification.md`` Enum Policy.
"""

from __future__ import annotations

from enum import Enum


class Market(Enum):
    """Trading venue that publishes the instrument."""

    A3 = "A3"  # A3 Mercados (formerly Matba Rofex)


class ProviderName(Enum):
    """Data provider that supplied an observation.

    The provider is metadata attached to the data; the rest of the Toolkit never
    branches on it. Adding a provider must not require changes elsewhere.
    """

    A3 = "A3"
    A3_PUBLIC_VIEWER = "A3_PUBLIC_VIEWER"
    IOL = "IOL"
    CSV = "CSV"
    MOCK = "MOCK"


class InstrumentClass(Enum):
    """Segment / instrument family. Extensible without touching the rest.

    The A3 / MAE MarketData API exposes the cash segments below. The futures
    families are kept for a future Matba Rofex / Primary provider.
    """

    # A3 / MAE MarketData segments (current scope)
    FIXED_INCOME = "FIXED_INCOME"  # rentafija
    CAUCION = "CAUCION"  # cauciones
    FOREX = "FOREX"  # forex (spot FX)
    REPO = "REPO"  # repo

    # Futures families (future Matba Rofex / Primary provider)
    FX_FUTURE = "FX_FUTURE"
    COMMODITY_FUTURE = "COMMODITY_FUTURE"
    RATE_FUTURE = "RATE_FUTURE"
    INDEX_FUTURE = "INDEX_FUTURE"


class ApiEnvironment(Enum):
    """A3 / MAE MarketData API environment."""

    UAT = "UAT"  # test environment
    PROD = "PROD"  # production


class PriceType(Enum):
    """Which price a view selects explicitly.

    There is no silent substitution: if the requested price is absent from a
    quote, the response reports it as missing instead of replacing it with a
    different price.
    """

    SETTLEMENT = "SETTLEMENT"  # official adjustment — preferred for daily history
    LAST = "LAST"  # last trade — intraday view
    BID = "BID"  # best bid — executable sell price
    ASK = "ASK"  # best ask — executable buy price
    MID = "MID"  # indicative — computed explicitly from bid/ask


class SyncStatus(Enum):
    """Outcome of a synchronization run."""

    OK = "OK"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class MethodologyStatus(Enum):
    """Research status of a derived (calculated) value.

    ``VALIDATED`` does NOT imply production approval. Production additionally
    requires an explicit ``Implementation Approved: Yes`` in the research record
    (project Research First Policy).
    """

    PENDING = "PENDING"  # no approved research
    UNDER_REVIEW = "UNDER_REVIEW"  # research open (e.g. R-009), not implementable
    VALIDATED = "VALIDATED"  # research validated


class CandidateOrigin(Enum):
    """How a Treasury-instrument candidate entered the lifecycle."""

    TREASURY_OFFICIAL = "TREASURY_OFFICIAL"
    MANUAL = "MANUAL"


class InstrumentLifecycleStatus(Enum):
    """Operational availability, deliberately separate from validation."""

    PENDING_SECONDARY_MARKET = "PENDING_SECONDARY_MARKET"
    PENDING_MATCH = "PENDING_MATCH"
    ACTIVE_FOR_ANALYSIS = "ACTIVE_FOR_ANALYSIS"
    MATURED = "MATURED"


class InstrumentMatchMethod(Enum):
    """Evidence used to associate a Treasury result with an A3 ticker."""

    NONE = "NONE"
    EXACT_TICKER = "EXACT_TICKER"
    UNIQUE_ATTRIBUTES = "UNIQUE_ATTRIBUTES"
    AMBIGUOUS = "AMBIGUOUS"
    RETAINED_ACTIVE = "RETAINED_ACTIVE"


class TreasuryInstrumentFamily(Enum):
    """National-Treasury families identifiable from explicit source wording."""

    LECAP = "LECAP"
    BONCAP = "BONCAP"
    LEDE = "LEDE"
    LECER = "LECER"
    LELINK = "LELINK"
    TREASURY_BILL = "TREASURY_BILL"
    TREASURY_BOND = "TREASURY_BOND"


class AuctionValueUnit(Enum):
    """Unit explicitly visible in a primary-market result cell."""

    PERCENT = "PERCENT"
    ARS = "ARS"
    USD = "USD"
    REPORTED_NUMBER = "REPORTED_NUMBER"
