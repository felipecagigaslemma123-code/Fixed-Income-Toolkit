"""Apply the approved Treasury-to-A3 operational activation rules."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Iterable, Optional, Tuple

from market_data.instrument_identity import (
    infer_currency,
    infer_instrument_family,
    normalize_a3_contract_ticker,
    normalize_ticker,
    parse_explicit_maturity_date,
)
from market_data.models.enums import (
    InstrumentClass,
    InstrumentLifecycleStatus,
    InstrumentMatchMethod,
    ProviderName,
)
from market_data.models.instrument_lifecycle import (
    ActivationEvidence,
    InstrumentLifecycleDecision,
    TreasuryInstrumentCandidate,
)
from market_data.models.quote import MarketQuote


def _quote_evidence(quote: MarketQuote) -> ActivationEvidence:
    return ActivationEvidence(
        ticker=quote.ticker,
        provider=quote.provider,
        market_date=quote.market_date,
        retrieved_at=quote.retrieved_at,
    )


class InstrumentActivationService:
    """Match official candidates to A3 visibility without financial inference."""

    def evaluate(
        self,
        candidate: TreasuryInstrumentCandidate,
        quotes: Iterable[MarketQuote],
        as_of: date,
        evaluated_at: datetime,
        previous: Optional[InstrumentLifecycleDecision] = None,
    ) -> InstrumentLifecycleDecision:
        """Return the candidate's current operational state.

        Exact ticker matching has priority and is mandatory when the official
        source supplies a ticker. Attribute fallback is allowed only when the
        source omitted the ticker and exactly one A3 ticker matches all three
        explicit attributes: family, currency and maturity date.
        """
        if candidate.maturity_date is not None and candidate.maturity_date <= as_of:
            return InstrumentLifecycleDecision(
                candidate=candidate,
                status=InstrumentLifecycleStatus.MATURED,
                match_method=InstrumentMatchMethod.NONE,
                matched_ticker=(previous.matched_ticker if previous else candidate.ticker),
                activation_evidence=(previous.activation_evidence if previous else None),
                evaluated_at=evaluated_at,
            )

        if previous and previous.status is InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS:
            return InstrumentLifecycleDecision(
                candidate=candidate,
                status=InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS,
                match_method=InstrumentMatchMethod.RETAINED_ACTIVE,
                matched_ticker=previous.matched_ticker,
                activation_evidence=previous.activation_evidence,
                evaluated_at=evaluated_at,
            )

        a3_quotes = tuple(
            quote
            for quote in quotes
            if quote.provider is ProviderName.A3
            and quote.instrument_class is InstrumentClass.FIXED_INCOME
            and normalize_a3_contract_ticker(quote.ticker, quote.term) is not None
        )
        quote_by_ticker: Dict[str, MarketQuote] = {}
        for quote in sorted(
            a3_quotes,
            key=lambda value: (value.market_date, value.retrieved_at, value.ticker),
        ):
            ticker = normalize_a3_contract_ticker(quote.ticker, quote.term)
            if ticker is not None and ticker not in quote_by_ticker:
                quote_by_ticker[ticker] = quote

        official_ticker = normalize_ticker(candidate.ticker)
        if official_ticker is not None:
            matched = quote_by_ticker.get(official_ticker)
            if matched is None:
                return InstrumentLifecycleDecision(
                    candidate=candidate,
                    status=InstrumentLifecycleStatus.PENDING_SECONDARY_MARKET,
                    match_method=InstrumentMatchMethod.NONE,
                    matched_ticker=None,
                    activation_evidence=None,
                    evaluated_at=evaluated_at,
                )
            return InstrumentLifecycleDecision(
                candidate=candidate,
                status=InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS,
                match_method=InstrumentMatchMethod.EXACT_TICKER,
                matched_ticker=official_ticker,
                activation_evidence=_quote_evidence(matched),
                evaluated_at=evaluated_at,
            )

        required_identity = (
            candidate.instrument_family,
            candidate.currency,
            candidate.maturity_date,
        )
        if any(value is None for value in required_identity):
            return InstrumentLifecycleDecision(
                candidate=candidate,
                status=InstrumentLifecycleStatus.PENDING_MATCH,
                match_method=InstrumentMatchMethod.NONE,
                matched_ticker=None,
                activation_evidence=None,
                evaluated_at=evaluated_at,
            )

        matches: Dict[str, MarketQuote] = {}
        for ticker, quote in quote_by_ticker.items():
            description = quote.description or ""
            identity = (
                infer_instrument_family(description),
                infer_currency(description, quote.currency),
                parse_explicit_maturity_date(description),
            )
            if identity == required_identity:
                matches[ticker] = quote

        if len(matches) == 1:
            matched_ticker, matched = next(iter(matches.items()))
            return InstrumentLifecycleDecision(
                candidate=candidate,
                status=InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS,
                match_method=InstrumentMatchMethod.UNIQUE_ATTRIBUTES,
                matched_ticker=matched_ticker,
                activation_evidence=_quote_evidence(matched),
                evaluated_at=evaluated_at,
            )

        return InstrumentLifecycleDecision(
            candidate=candidate,
            status=InstrumentLifecycleStatus.PENDING_MATCH,
            match_method=(
                InstrumentMatchMethod.AMBIGUOUS
                if len(matches) > 1
                else InstrumentMatchMethod.NONE
            ),
            matched_ticker=None,
            activation_evidence=None,
            evaluated_at=evaluated_at,
        )

    def evaluate_all(
        self,
        candidates: Iterable[TreasuryInstrumentCandidate],
        quotes: Iterable[MarketQuote],
        as_of: date,
        evaluated_at: datetime,
        previous: Iterable[InstrumentLifecycleDecision] = (),
    ) -> Tuple[InstrumentLifecycleDecision, ...]:
        """Evaluate many candidates deterministically and preserve sticky states."""
        quote_tuple = tuple(quotes)
        previous_by_source = {
            item.candidate.source_id: item for item in previous
        }
        return tuple(
            self.evaluate(
                candidate,
                quote_tuple,
                as_of,
                evaluated_at,
                previous_by_source.get(candidate.source_id),
            )
            for candidate in candidates
        )
