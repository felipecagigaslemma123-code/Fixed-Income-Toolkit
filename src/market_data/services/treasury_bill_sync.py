"""Orchestrate Treasury discovery and A3 operational activation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional, Protocol, Tuple

from market_data.models.enums import InstrumentClass, InstrumentLifecycleStatus
from market_data.models.instrument_lifecycle import (
    InstrumentLifecycleDecision,
    TreasuryInstrumentCandidate,
    TreasuryResultNotice,
)
from market_data.models.quote import MarketQuote
from market_data.providers.base import QuoteQuery
from market_data.services.instrument_lifecycle import InstrumentActivationService
from market_data.storage.base import MarketDataRepository
from market_data.storage.lifecycle_repository import InstrumentLifecycleRepository


class TreasuryResultSource(Protocol):
    def list_result_notices(self) -> Tuple[TreasuryResultNotice, ...]:
        ...

    def fetch_candidates(
        self, notice: TreasuryResultNotice
    ) -> Tuple[TreasuryInstrumentCandidate, ...]:
        ...


class FixedIncomeQuoteSource(Protocol):
    def fetch_quotes(self, query: QuoteQuery) -> Tuple[MarketQuote, ...]:
        ...


@dataclass(frozen=True)
class TreasuryBillSyncResult:
    """Counts and decisions from one idempotent synchronization run."""

    notices_checked: int
    quotes_received: int
    quotes_saved: int
    candidates_evaluated: int
    active_for_analysis: int
    pending_secondary_market: int
    pending_match: int
    matured: int
    decisions: Tuple[InstrumentLifecycleDecision, ...]


@dataclass(frozen=True)
class TreasuryDiscoveryResult:
    """Outcome of the independent daily official-source refresh."""

    notices_checked: int
    candidates_discovered: int
    decisions: Tuple[InstrumentLifecycleDecision, ...]


@dataclass(frozen=True)
class A3ActivationResult:
    """Outcome of one independent A3 fixed-income refresh."""

    quotes_received: int
    quotes_saved: int
    candidates_evaluated: int
    active_for_analysis: int
    pending_secondary_market: int
    pending_match: int
    matured: int
    decisions: Tuple[InstrumentLifecycleDecision, ...]


class TreasuryBillSyncService:
    """Fetch source data, reconcile identities and persist lifecycle states."""

    def __init__(
        self,
        treasury_source: TreasuryResultSource,
        quote_source: FixedIncomeQuoteSource,
        repository: InstrumentLifecycleRepository,
        activation_service: Optional[InstrumentActivationService] = None,
        quote_repository: Optional[MarketDataRepository] = None,
    ) -> None:
        self._treasury_source = treasury_source
        self._quote_source = quote_source
        self._repository = repository
        self._activation_service = activation_service or InstrumentActivationService()
        self._quote_repository = quote_repository

    def refresh_treasury(
        self,
        as_of: Optional[date] = None,
        evaluated_at: Optional[datetime] = None,
        max_result_articles: Optional[int] = None,
    ) -> TreasuryDiscoveryResult:
        """Refresh official candidates without calling A3."""
        run_at = evaluated_at or datetime.now(timezone.utc)
        valuation_date = as_of or run_at.date()
        notices = self._treasury_source.list_result_notices()
        if max_result_articles is not None:
            notices = notices[:max_result_articles]

        discovered = []
        for notice in notices:
            discovered.extend(self._treasury_source.fetch_candidates(notice))

        previous = self._repository.get_all()
        candidate_by_source = {
            item.candidate.source_id: item.candidate for item in previous
        }
        for candidate in discovered:
            candidate_by_source[candidate.source_id] = candidate

        decisions = self._activation_service.evaluate_all(
            candidate_by_source.values(),
            (),
            valuation_date,
            run_at,
            previous,
        )
        self._repository.save_decisions(decisions)
        return TreasuryDiscoveryResult(
            notices_checked=len(notices),
            candidates_discovered=len(discovered),
            decisions=decisions,
        )

    def refresh_a3(
        self,
        as_of: Optional[date] = None,
        evaluated_at: Optional[datetime] = None,
    ) -> A3ActivationResult:
        """Refresh A3 quotes and re-evaluate stored candidates without Treasury."""
        run_at = evaluated_at or datetime.now(timezone.utc)
        valuation_date = as_of or run_at.date()
        previous = self._repository.get_all()
        quotes = self._quote_source.fetch_quotes(
            QuoteQuery(instrument_class=InstrumentClass.FIXED_INCOME)
        )
        quotes_saved = (
            0
            if self._quote_repository is None
            else self._quote_repository.save_quotes(quotes)
        )
        decisions = self._activation_service.evaluate_all(
            (item.candidate for item in previous),
            quotes,
            valuation_date,
            run_at,
            previous,
        )
        self._repository.save_decisions(decisions)

        def count(status: InstrumentLifecycleStatus) -> int:
            return sum(1 for item in decisions if item.status is status)

        return A3ActivationResult(
            quotes_received=len(quotes),
            quotes_saved=quotes_saved,
            candidates_evaluated=len(decisions),
            active_for_analysis=count(InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS),
            pending_secondary_market=count(
                InstrumentLifecycleStatus.PENDING_SECONDARY_MARKET
            ),
            pending_match=count(InstrumentLifecycleStatus.PENDING_MATCH),
            matured=count(InstrumentLifecycleStatus.MATURED),
            decisions=decisions,
        )

    def run(
        self,
        as_of: Optional[date] = None,
        evaluated_at: Optional[datetime] = None,
        max_result_articles: Optional[int] = None,
    ) -> TreasuryBillSyncResult:
        """Run one read-only provider synchronization and persist its decisions."""
        run_at = evaluated_at or datetime.now(timezone.utc)
        treasury = self.refresh_treasury(
            as_of=as_of,
            evaluated_at=run_at,
            max_result_articles=max_result_articles,
        )
        a3 = self.refresh_a3(as_of=as_of, evaluated_at=run_at)
        return TreasuryBillSyncResult(
            notices_checked=treasury.notices_checked,
            quotes_received=a3.quotes_received,
            quotes_saved=a3.quotes_saved,
            candidates_evaluated=a3.candidates_evaluated,
            active_for_analysis=a3.active_for_analysis,
            pending_secondary_market=a3.pending_secondary_market,
            pending_match=a3.pending_match,
            matured=a3.matured,
            decisions=a3.decisions,
        )
