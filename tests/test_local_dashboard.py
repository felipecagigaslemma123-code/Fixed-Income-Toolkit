"""Tests for the loopback-only HTML/SQLite bridge."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from local_dashboard.data import lifecycle_payload, market_quotes_payload
from local_dashboard.server import create_server
from market_data.models.enums import (
    CandidateOrigin,
    InstrumentClass,
    InstrumentLifecycleStatus,
    InstrumentMatchMethod,
    ProviderName,
    TreasuryInstrumentFamily,
)
from market_data.models.instrument_lifecycle import (
    ActivationEvidence,
    InstrumentLifecycleDecision,
    TreasuryInstrumentCandidate,
)
from market_data.models.quote import MarketQuote
from market_data.storage.lifecycle_repository import SqliteLifecycleRepository
from market_data.storage.sqlite_repository import SqliteRepository

_NOW = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _quote() -> MarketQuote:
    return MarketQuote(
        ticker="S16O6",
        description="LECAP",
        issue_type="TPN",
        segment="Bilateral TRD",
        segment_code="BT",
        term="001",
        term_code="001",
        currency="$",
        market_date=date(2026, 8, 10),
        settlement_date=date(2026, 8, 11),
        last_price=Decimal("101.2500"),
        close_price=None,
        previous_close=Decimal("100.95"),
        min_price=Decimal("101.00"),
        max_price=Decimal("101.30"),
        provider_rate=Decimal("0"),
        accumulated_volume=Decimal("250000"),
        accumulated_amount=Decimal("253125"),
        open_interest=Decimal("0"),
        variation=Decimal("0.30"),
        bid=None,
        ask=None,
        instrument_class=InstrumentClass.FIXED_INCOME,
        provider=ProviderName.A3,
        retrieved_at=_NOW,
    )


def _decision() -> InstrumentLifecycleDecision:
    candidate = TreasuryInstrumentCandidate(
        source_id="official#s16o6",
        origin=CandidateOrigin.TREASURY_OFFICIAL,
        description="LETRA CAPITALIZABLE EN PESOS",
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


class LocalDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "market.sqlite"
        with SqliteRepository(str(self.database)) as quotes:
            quotes.initialize()
            quotes.save_quotes([_quote()])
        with SqliteLifecycleRepository(str(self.database)) as lifecycle:
            lifecycle.initialize()
            lifecycle.save_decisions([_decision()])

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_payloads_preserve_decimal_strings_and_operational_state(self) -> None:
        quotes = market_quotes_payload(str(self.database))
        quote = quotes["quotes"][0]
        self.assertEqual(quote["last_price"], "101.2500")
        self.assertIsInstance(quote["last_price"], str)
        self.assertIsNone(quote["close_price"])
        self.assertEqual(quote["term"], "001")
        self.assertTrue(quotes["price_selection_is_explicit"])
        self.assertFalse(quotes["silent_price_fallback"])

        lifecycle = lifecycle_payload(str(self.database))
        instrument = lifecycle["instruments"][0]
        self.assertEqual(instrument["lifecycle_status"], "ACTIVE_FOR_ANALYSIS")
        self.assertEqual(instrument["activation_provider"], "A3")
        self.assertTrue(
            lifecycle["operational_state_is_not_financial_validation"]
        )

    def test_server_exposes_only_allowlisted_routes(self) -> None:
        dashboard = _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        server = create_server(dashboard, self.database, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:{}".format(server.server_address[1])
        try:
            with urlopen(base + "/", timeout=2) as response:
                html = response.read().decode("utf-8")
            self.assertIn("Modelo LECAP / BONCAP", html)
            self.assertIn("/api/market/quotes", html)
            self.assertNotIn("data912.com", html)

            with urlopen(base + "/api/market/quotes", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["quotes"][0]["last_price"], "101.2500")

            with urlopen(base + "/api/health", timeout=2) as response:
                health = json.loads(response.read().decode("utf-8"))
            self.assertEqual(health["status"], "ok")
            self.assertEqual(health["quote_count"], 1)

            with self.assertRaises(HTTPError) as context:
                urlopen(base + "/%2e%2e/.env", timeout=2)
            self.assertEqual(context.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_dashboard_keeps_manual_and_fifteen_minute_refresh(self) -> None:
        html = (
            _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        ).read_text(encoding="utf-8")
        self.assertIn("id=\"refreshbtn\"", html)
        self.assertIn("const REFRESH_INTERVAL_MS = 15*60*1000", html)
        self.assertIn("setInterval(()=>refreshLocalData(false),REFRESH_INTERVAL_MS)", html)
        self.assertIn('PRICE_BASIS = "last"', html)
        self.assertIn("q[field]", html)
        self.assertNotIn("mid||", html)

    def test_dashboard_maps_a3_24_hour_ticker_to_contract_identity(self) -> None:
        html = (
            _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        ).read_text(encoding="utf-8")
        self.assertIn("function contractTickerFromA3(q)", html)
        self.assertIn("isExplicitT1(q)&&ticker.endsWith('/24HS')", html)
        self.assertIn("ticker.slice(0,-5)", html)
        self.assertIn("latestByTicker[contractTicker]", html)
        self.assertIn("function isSupportedA3T1Price(q)", html)
        self.assertIn(".filter(isSupportedA3T1Price)", html)

    def test_manual_refresh_uses_latest_market_date_with_explicit_warning(self) -> None:
        html = (
            _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        ).read_text(encoding="utf-8")
        self.assertIn("let DEFAULT_TRADE = todayISO()", html)
        self.assertIn(
            "$('refreshbtn').addEventListener('click',()=>refreshLocalData(true))",
            html,
        )
        self.assertIn(
            "if(resetTradeDate&&latestMarketDate)DEFAULT_TRADE=latestMarketDate",
            html,
        )
        self.assertIn("⚠ mostrando el último día disponible", html)
        self.assertIn("observación A3 ${fmtDateLong(latestMarketDate)}", html)
        self.assertIn("snapshots históricos visibles, tasas corrientes deshabilitadas", html)
        self.assertNotIn("DEFAULT_TRADE=SNAPSHOT_DATE", html)

    def test_dashboard_blocks_temporally_mixed_current_yields(self) -> None:
        """The guard moved to the service; the HTML must still disclose it.

        The temporal-alignment rule itself is pinned in
        ``tests/test_dashboard_metrics.py`` against the engine. Here we only
        check the dashboard keeps telling the user when rates are suppressed.
        """
        html = (
            _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        ).read_text(encoding="utf-8")
        self.assertIn("price_date", html)
        self.assertIn("yield_available", html)
        self.assertIn("Tasas no calculadas.", html)
        self.assertIn("tasas corrientes deshabilitadas", html)

    def test_dashboard_contains_no_financial_formula(self) -> None:
        """The HTML renders; it must not re-implement the engine.

        A second implementation in JavaScript drifts from the Decimal engine:
        the 11 August 2026 TNA correction had to be applied twice. The
        dashboard now calls ``/api/metrics`` and holds no formula and no
        holiday calendar of its own.
        """
        html = (
            _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        ).read_text(encoding="utf-8")
        self.assertIn('const LOCAL_METRICS_ENDPOINT = "/api/metrics"', html)
        self.assertIn("async function fetchMetrics(", html)
        for formula in (
            "Math.pow(",
            "function days360(",
            "function workday(",
            "const HOLIDAYS",
            "function metrics(",
            "rateReady",
        ):
            with self.subTest(formula=formula):
                self.assertNotIn(formula, html)

    def test_dashboard_includes_s16o6_from_latest_iamc_report(self) -> None:
        html = (
            _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        ).read_text(encoding="utf-8")
        self.assertIn('{ticker:"S16O6",type:"LECAP"', html)
        self.assertIn('issue:"2026-07-31",maturity:"2026-10-16"', html)
        self.assertIn('tem_issue:0.0205,price:100.7,price_date:"2026-08-10"', html)

    def test_legacy_html_redirects_to_the_current_dashboard(self) -> None:
        legacy = (_REPO_ROOT / "outputs" / "lecap_model.html").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '<meta http-equiv="refresh" content="0; url=modelo_lecap_boncap.html">',
            legacy,
        )

    def test_dashboard_hides_matured_contracts_from_current_views(self) -> None:
        html = (
            _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        ).read_text(encoding="utf-8")
        self.assertIn("function isCurrentMaturity(maturity,asOf=todayISO())", html)
        self.assertIn("maturity>asOf", html)
        self.assertIn("function currentContractData()", html)
        self.assertIn("async function computeAll(trade)", html)
        self.assertIn("currentContractData().map", html)
        self.assertIn("fillPicker('S31G6')", html)

    def test_dashboard_exposes_only_current_national_treasury_lifecycle(self) -> None:
        html = (
            _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
        ).read_text(encoding="utf-8")
        self.assertIn('id="treasuryUniverse"', html)
        self.assertIn("x.origin==='TREASURY_OFFICIAL'", html)
        self.assertIn("x.lifecycle_status!=='MATURED'", html)
        self.assertIn("'Fuera del cálculo LECAP/BONCAP'", html)
        self.assertIn("'Faltan datos contractuales'", html)

    def test_macos_launcher_uses_read_only_production_market_visibility(self) -> None:
        launcher = (_REPO_ROOT / "Abrir Modelo LECAP BONCAP.command").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "tools/run_local_toolkit.py --environment PROD --allow-production",
            launcher,
        )


if __name__ == "__main__":
    unittest.main()
