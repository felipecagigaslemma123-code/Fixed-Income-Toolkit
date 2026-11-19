"""Tests for the owner-approved Treasury-to-A3 activation hierarchy."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

from market_data.models.enums import (
    CandidateOrigin,
    InstrumentClass,
    InstrumentLifecycleStatus,
    InstrumentMatchMethod,
    ProviderName,
    TreasuryInstrumentFamily,
)
from market_data.models.instrument_lifecycle import TreasuryInstrumentCandidate
from market_data.models.quote import MarketQuote
from market_data.services.instrument_lifecycle import InstrumentActivationService

_NOW = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)


def _candidate(ticker="S16O6"):
    return TreasuryInstrumentCandidate(
        source_id="official#1",
        origin=CandidateOrigin.TREASURY_OFFICIAL,
        description="LETRA DEL TESORO NACIONAL CAPITALIZABLE EN PESOS CON VENCIMIENTO 16 DE OCTUBRE DE 2026",
        ticker=ticker,
        instrument_family=TreasuryInstrumentFamily.LECAP,
        currency="ARS",
        maturity_date=date(2026, 10, 16),
        auction_date=date(2026, 7, 29),
        issue_action="NUEVA",
        source_url="https://www.argentina.gob.ar/noticias/result",
        source_title="Resultado oficial",
        source_fields=(),
        discovered_at=_NOW,
    )


def _quote(ticker="S16O6", description=None, price="0", term="001"):
    return MarketQuote(
        ticker=ticker,
        description=description or "LECAP EN PESOS VENCIMIENTO 16 DE OCTUBRE DE 2026",
        issue_type="TPN",
        segment="Bilateral TRD",
        segment_code="BT",
        term=term,
        term_code=term,
        currency="$",
        market_date=date(2026, 8, 10),
        settlement_date=None,
        last_price=Decimal(price),
        close_price=None,
        previous_close=Decimal("0"),
        min_price=Decimal("0"),
        max_price=Decimal("0"),
        provider_rate=Decimal("0"),
        accumulated_volume=Decimal("0"),
        accumulated_amount=Decimal("0"),
        open_interest=Decimal("0"),
        variation=Decimal("0"),
        bid=None,
        ask=None,
        instrument_class=InstrumentClass.FIXED_INCOME,
        provider=ProviderName.A3,
        retrieved_at=_NOW,
    )


class InstrumentActivationTests(unittest.TestCase):
    def setUp(self):
        self.service = InstrumentActivationService()

    def test_exact_ticker_activates_even_with_zero_price_and_volume(self):
        decision = self.service.evaluate(
            _candidate(), [_quote()], date(2026, 8, 10), _NOW
        )
        self.assertIs(decision.status, InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS)
        self.assertIs(decision.match_method, InstrumentMatchMethod.EXACT_TICKER)
        self.assertEqual(decision.matched_ticker, "S16O6")
        self.assertIsNotNone(decision.activation_evidence)

    def test_known_ticker_requires_exact_a3_match(self):
        decision = self.service.evaluate(
            _candidate(), [_quote(ticker="OTHER")], date(2026, 8, 10), _NOW
        )
        self.assertIs(
            decision.status, InstrumentLifecycleStatus.PENDING_SECONDARY_MARKET
        )
        self.assertIsNone(decision.matched_ticker)

    def test_a3_24_hour_suffix_matches_same_contract_without_losing_raw_evidence(self):
        decision = self.service.evaluate(
            _candidate(),
            [_quote(ticker="S16O6/24hs", term="001")],
            date(2026, 8, 10),
            _NOW,
        )
        self.assertIs(decision.status, InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS)
        self.assertIs(decision.match_method, InstrumentMatchMethod.EXACT_TICKER)
        self.assertEqual(decision.matched_ticker, "S16O6")
        self.assertEqual(decision.activation_evidence.ticker, "S16O6/24hs")

    def test_a3_24_hour_suffix_requires_explicit_term_001(self):
        decision = self.service.evaluate(
            _candidate(),
            [_quote(ticker="S16O6/24hs", term="000")],
            date(2026, 8, 10),
            _NOW,
        )
        self.assertIs(
            decision.status, InstrumentLifecycleStatus.PENDING_SECONDARY_MARKET
        )

    def test_a3_suffix_mapping_does_not_merge_a_different_contract_prefix(self):
        decision = self.service.evaluate(
            _candidate(),
            [_quote(ticker="X16O6/24hs", term="001")],
            date(2026, 8, 10),
            _NOW,
        )
        self.assertIs(
            decision.status, InstrumentLifecycleStatus.PENDING_SECONDARY_MARKET
        )

    def test_missing_ticker_uses_unique_attributes(self):
        candidate = replace(_candidate(), ticker=None)
        quotes = [
            _quote(ticker="S16O6", term="000"),
            _quote(ticker="S16O6", term="001"),
            _quote(
                ticker="S30O6",
                description="LECAP EN PESOS VENCIMIENTO 30 DE OCTUBRE DE 2026",
            ),
        ]
        decision = self.service.evaluate(candidate, quotes, date(2026, 8, 10), _NOW)
        self.assertIs(decision.status, InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS)
        self.assertIs(decision.match_method, InstrumentMatchMethod.UNIQUE_ATTRIBUTES)
        self.assertEqual(decision.matched_ticker, "S16O6")

    def test_missing_ticker_remains_pending_when_ambiguous(self):
        candidate = replace(_candidate(), ticker=None)
        decision = self.service.evaluate(
            candidate,
            [_quote(ticker="ONE"), _quote(ticker="TWO")],
            date(2026, 8, 10),
            _NOW,
        )
        self.assertIs(decision.status, InstrumentLifecycleStatus.PENDING_MATCH)
        self.assertIs(decision.match_method, InstrumentMatchMethod.AMBIGUOUS)

    def test_active_state_is_sticky_when_a3_response_is_later_empty(self):
        active = self.service.evaluate(
            _candidate(), [_quote()], date(2026, 8, 10), _NOW
        )
        later = self.service.evaluate(
            _candidate(), [], date(2026, 8, 11), _NOW.replace(day=11), active
        )
        self.assertIs(later.status, InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS)
        self.assertIs(later.match_method, InstrumentMatchMethod.RETAINED_ACTIVE)
        self.assertEqual(later.activation_evidence, active.activation_evidence)

    def test_instrument_matures_on_or_after_maturity_date(self):
        # Owner convention (2026-08-10): a letra is MATURED on its maturity date
        # itself (it settles/pays and no longer trades that day).
        before_maturity = self.service.evaluate(
            _candidate(), [], date(2026, 10, 15), _NOW
        )
        on_maturity = self.service.evaluate(
            _candidate(), [], date(2026, 10, 16), _NOW
        )
        after_maturity = self.service.evaluate(
            _candidate(), [], date(2026, 10, 17), _NOW
        )
        self.assertIs(
            before_maturity.status,
            InstrumentLifecycleStatus.PENDING_SECONDARY_MARKET,
        )
        self.assertIs(on_maturity.status, InstrumentLifecycleStatus.MATURED)
        self.assertIs(after_maturity.status, InstrumentLifecycleStatus.MATURED)


if __name__ == "__main__":
    unittest.main()
