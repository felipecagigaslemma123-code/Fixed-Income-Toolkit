"""SQLite lifecycle persistence and Decimal evidence round-trip tests."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from market_data.models.enums import (
    AuctionValueUnit,
    CandidateOrigin,
    InstrumentLifecycleStatus,
    InstrumentMatchMethod,
    ProviderName,
    TreasuryInstrumentFamily,
)
from market_data.models.instrument_lifecycle import (
    ActivationEvidence,
    InstrumentLifecycleDecision,
    SourceField,
    TreasuryInstrumentCandidate,
)
from market_data.storage import (
    InstrumentLifecycleRepository,
    SqliteLifecycleRepository,
)

_NOW = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)


def _decision():
    candidate = TreasuryInstrumentCandidate(
        source_id="official#table-1-row-1",
        origin=CandidateOrigin.TREASURY_OFFICIAL,
        description="LETRA DEL TESORO ... (S16O6 - nueva)",
        ticker="S16O6",
        instrument_family=TreasuryInstrumentFamily.LECAP,
        currency="ARS",
        maturity_date=date(2026, 10, 16),
        auction_date=date(2026, 7, 29),
        issue_action="NUEVA",
        source_url="https://www.argentina.gob.ar/noticias/result",
        source_title="Resultado oficial",
        source_fields=(
            SourceField(
                header="TEM de corte",
                raw_value="2,05%",
                decimal_value=Decimal("2.05"),
                unit=AuctionValueUnit.PERCENT,
            ),
        ),
        discovered_at=_NOW,
    )
    return InstrumentLifecycleDecision(
        candidate=candidate,
        status=InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS,
        match_method=InstrumentMatchMethod.EXACT_TICKER,
        matched_ticker="S16O6",
        activation_evidence=ActivationEvidence(
            ticker="S16O6",
            provider=ProviderName.A3,
            market_date=date(2026, 8, 10),
            retrieved_at=_NOW,
        ),
        evaluated_at=_NOW,
    )


class LifecycleRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = SqliteLifecycleRepository(":memory:")
        self.repository.initialize()

    def tearDown(self):
        self.repository.close()

    def test_repository_satisfies_protocol(self):
        self.assertIsInstance(self.repository, InstrumentLifecycleRepository)

    def test_round_trip_preserves_raw_evidence_and_decimal(self):
        self.assertEqual(self.repository.save_decisions([_decision()]), 1)
        restored = self.repository.get_by_source_id("official#table-1-row-1")
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertIs(restored.status, InstrumentLifecycleStatus.ACTIVE_FOR_ANALYSIS)
        self.assertEqual(restored.matched_ticker, "S16O6")
        field = restored.candidate.source_fields[0]
        self.assertEqual(field.raw_value, "2,05%")
        self.assertEqual(field.decimal_value, Decimal("2.05"))
        self.assertIsInstance(field.decimal_value, Decimal)
        self.assertIs(field.unit, AuctionValueUnit.PERCENT)

    def test_save_is_idempotent_by_source_id(self):
        self.repository.save_decisions([_decision()])
        self.repository.save_decisions([_decision()])
        self.assertEqual(len(self.repository.get_all()), 1)

    def test_manual_candidate_requires_explicit_reference(self):
        with self.assertRaises(ValueError):
            TreasuryInstrumentCandidate(
                source_id="manual#1",
                origin=CandidateOrigin.MANUAL,
                description="Manual candidate",
                ticker="S16O6",
                instrument_family=TreasuryInstrumentFamily.LECAP,
                currency="ARS",
                maturity_date=date(2026, 10, 16),
                auction_date=date(2026, 7, 29),
                issue_action="NUEVA",
                source_url=None,
                source_title="Manual input",
                source_fields=(),
                discovered_at=_NOW,
                manual_reference=None,
            )


if __name__ == "__main__":
    unittest.main()
