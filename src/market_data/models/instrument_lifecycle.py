"""Treasury-instrument discovery and operational-lifecycle models.

These models represent source evidence and the decision to make an instrument
available to the Toolkit. ``ACTIVE_FOR_ANALYSIS`` is an operational state only;
it never implies that contractual data or a financial methodology is validated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Tuple

from market_data.models.enums import (
    AuctionValueUnit,
    CandidateOrigin,
    InstrumentLifecycleStatus,
    InstrumentMatchMethod,
    ProviderName,
    TreasuryInstrumentFamily,
)


@dataclass(frozen=True)
class SourceField:
    """One source table cell, preserving both its label and exact raw text."""

    header: str
    raw_value: str
    decimal_value: Optional[Decimal]
    unit: Optional[AuctionValueUnit]


@dataclass(frozen=True)
class TreasuryResultNotice:
    """A result article discovered in the official finance-news listing."""

    title: str
    publication_date: date
    url: str


@dataclass(frozen=True)
class TreasuryInstrumentCandidate:
    """A Treasury Bill staged from official or explicitly manual evidence."""

    source_id: str
    origin: CandidateOrigin
    description: str
    ticker: Optional[str]
    instrument_family: Optional[TreasuryInstrumentFamily]
    currency: Optional[str]
    maturity_date: Optional[date]
    auction_date: date
    issue_action: Optional[str]
    source_url: Optional[str]
    source_title: str
    source_fields: Tuple[SourceField, ...]
    discovered_at: datetime
    manual_reference: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.description.strip():
            raise ValueError("description must not be empty")
        if self.origin is CandidateOrigin.TREASURY_OFFICIAL and not self.source_url:
            raise ValueError("Official candidates require source_url")
        if self.origin is CandidateOrigin.MANUAL and not (
            self.manual_reference and self.manual_reference.strip()
        ):
            raise ValueError("Manual candidates require manual_reference")


@dataclass(frozen=True)
class ActivationEvidence:
    """A3 observation that made a candidate operationally active."""

    ticker: str
    provider: ProviderName
    market_date: date
    retrieved_at: datetime


@dataclass(frozen=True)
class InstrumentLifecycleDecision:
    """Current operational state and its auditable matching evidence."""

    candidate: TreasuryInstrumentCandidate
    status: InstrumentLifecycleStatus
    match_method: InstrumentMatchMethod
    matched_ticker: Optional[str]
    activation_evidence: Optional[ActivationEvidence]
    evaluated_at: datetime
