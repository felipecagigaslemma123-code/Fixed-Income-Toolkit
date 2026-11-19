"""Offline end-to-end test for Treasury discovery plus A3 visibility."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from market_data.models.enums import (
    CandidateOrigin,
    InstrumentClass,
    InstrumentLifecycleStatus,
    ProviderName,
    TreasuryInstrumentFamily,
)
from market_data.models.instrument_lifecycle import TreasuryInstrumentCandidate, TreasuryResultNotice
from market_data.models.quote import MarketQuote
from market_data.services import TreasuryBillSyncService
from market_data.storage import SqliteLifecycleRepository, SqliteRepository

_NOW = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)


def _candidate():
    return TreasuryInstrumentCandidate(
        source_id="official#1",
        origin=CandidateOrigin.TREASURY_OFFICIAL,
        description="LETRA DEL TESORO NACIONAL CAPITALIZABLE EN PESOS CON VENCIMIENTO 16 DE OCTUBRE DE 2026 (S16O6 - nueva)",
        ticker="S16O6",
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


def _quote():
    return MarketQuote(
        ticker="S16O6",
        description="LECAP EN PESOS VENCIMIENTO 16 DE OCTUBRE DE 2026",
        issue_type="TPN",
        segment="Bilateral TRD",
        segment_code="BT",
        term="001",
        term_code="001",
        currency="$",
        market_date=date(2026, 8, 10),
        settlement_date=None,
        last_price=Decimal("0"),
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


class _TreasurySource:
    def __init__(self):
        self.calls = 0

    def list_result_notices(self):
        self.calls += 1
        return (
            TreasuryResultNotice(
                title="Resultado oficial",
                publication_date=date(2026, 7, 29),
                url="https://www.argentina.gob.ar/noticias/result",
            ),
        )

    def fetch_candidates(self, notice):
        return (_candidate(),)


class _QuoteSource:
    def __init__(self):
        self.calls = 0

    def fetch_quotes(self, query):
        self.calls += 1
        if query.instrument_class is not InstrumentClass.FIXED_INCOME:
            raise AssertionError("sync must request fixed income")
        return (_quote(),)


class TreasuryBillSyncTests(unittest.TestCase):
    def test_sync_activates_and_persists_without_financial_calculation(self):
        repository = SqliteLifecycleRepository(":memory:")
        repository.initialize()
        treasury = _TreasurySource()
        quotes = _QuoteSource()
        service = TreasuryBillSyncService(treasury, quotes, repository)
        try:
            first = service.run(as_of=date(2026, 8, 10), evaluated_at=_NOW)
            second = service.run(as_of=date(2026, 8, 10), evaluated_at=_NOW)
            self.assertEqual(first.notices_checked, 1)
            self.assertEqual(first.quotes_received, 1)
            self.assertEqual(first.quotes_saved, 0)
            self.assertEqual(first.candidates_evaluated, 1)
            self.assertEqual(first.active_for_analysis, 1)
            self.assertEqual(first.pending_match, 0)
            self.assertEqual(second.active_for_analysis, 1)
            self.assertEqual(treasury.calls, 2)
            self.assertEqual(quotes.calls, 2)
            self.assertEqual(len(repository.get_all()), 1)
            self.assertIs(
                repository.get_all()[0].status,
                InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS,
            )
        finally:
            repository.close()

    def test_daily_treasury_and_a3_refreshes_are_independent(self):
        repository = SqliteLifecycleRepository(":memory:")
        repository.initialize()
        quote_repository = SqliteRepository(":memory:")
        quote_repository.initialize()
        treasury = _TreasurySource()
        quotes = _QuoteSource()
        service = TreasuryBillSyncService(
            treasury,
            quotes,
            repository,
            quote_repository=quote_repository,
        )
        try:
            discovery = service.refresh_treasury(
                as_of=date(2026, 8, 10), evaluated_at=_NOW
            )
            self.assertEqual(discovery.candidates_discovered, 1)
            self.assertEqual(treasury.calls, 1)
            self.assertEqual(quotes.calls, 0)
            self.assertIs(
                repository.get_all()[0].status,
                InstrumentLifecycleStatus.PENDING_SECONDARY_MARKET,
            )

            activation = service.refresh_a3(
                as_of=date(2026, 8, 10), evaluated_at=_NOW
            )
            self.assertEqual(treasury.calls, 1)
            self.assertEqual(quotes.calls, 1)
            self.assertEqual(activation.quotes_received, 1)
            self.assertEqual(activation.quotes_saved, 1)
            self.assertEqual(activation.active_for_analysis, 1)
            stored_quotes = quote_repository.get_quotes(
                "S16O6", date(2026, 8, 10), date(2026, 8, 10)
            )
            self.assertEqual(len(stored_quotes), 1)
            self.assertEqual(stored_quotes[0].last_price, Decimal("0"))
        finally:
            repository.close()
            quote_repository.close()


if __name__ == "__main__":
    unittest.main()
