"""Tests for the dashboard metrics path.

The dashboard HTML no longer computes anything: these tests pin that the single
calculation path is the validated engine, that the temporal-alignment guard of
``docs/local_dashboard.md`` still blocks yields, and that no financial value is
serialized through binary floating point.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from financial_engine.duration import DurationInput, calculate_duration
from financial_engine.letras_yield import LetraYieldInput, calculate_letra_yield
from financial_engine.maturity_value import (
    InstrumentType,
    MaturityValueInput,
    calculate_maturity_value,
)
from local_dashboard.market_calendar import next_business_day
from local_dashboard.metrics import (
    DashboardMetricsInput,
    MetricsRequestError,
    compute_dashboard_metrics,
    metrics_payload,
)
from local_dashboard.server import create_server

_REPO_ROOT = Path(__file__).resolve().parent.parent

# S16O6 as documented in docs/research/iamc_yield_methodology_validation_2026-08-11.md
_S16O6 = dict(
    issue_date=date(2026, 7, 31),
    maturity_date=date(2026, 10, 16),
    monthly_issue_rate=Decimal("0.0205"),
    market_price=Decimal("100.68"),
    trade_date=date(2026, 8, 10),
    price_date=date(2026, 8, 10),
    provider_settlement_date=date(2026, 8, 11),
)


def _input(**overrides) -> DashboardMetricsInput:
    data = dict(_S16O6)
    data.update(overrides)
    return DashboardMetricsInput(instrument_type=InstrumentType.LECAP, **data)


class TestEngineIsTheOnlyCalculationPath(unittest.TestCase):
    """The module must return exactly what the engine returns, not a copy."""

    def test_values_match_the_engine_called_directly(self) -> None:
        result = compute_dashboard_metrics(_input())

        maturity = calculate_maturity_value(
            MaturityValueInput(
                instrument_type=InstrumentType.LECAP,
                issue_date=_S16O6["issue_date"],
                maturity_date=_S16O6["maturity_date"],
                monthly_issue_rate=_S16O6["monthly_issue_rate"],
                reference_face_value=Decimal(100),
                official_maturity_value=Decimal(0),
                source_reference="test",
            )
        )
        yields = calculate_letra_yield(
            LetraYieldInput(
                market_price=_S16O6["market_price"],
                settlement_date=_S16O6["provider_settlement_date"],
                maturity_date=_S16O6["maturity_date"],
                maturity_value=maturity.maturity_value,
                source_reference="test",
            )
        )
        duration = calculate_duration(
            DurationInput(
                settlement_date=_S16O6["provider_settlement_date"],
                maturity_date=_S16O6["maturity_date"],
                tea=yields.tea,
                compounding_frequency=12,
                source_reference="test",
            )
        )

        self.assertEqual(result.maturity_value, maturity.maturity_value)
        self.assertEqual(result.holding_period_return, yields.holding_period_return)
        self.assertEqual(result.tna, yields.tna)
        self.assertEqual(result.tea, yields.tea)
        self.assertEqual(result.tem, yields.tem)
        self.assertEqual(result.residual_days_actual, yields.residual_days_actual)
        self.assertEqual(result.macaulay_years, duration.macaulay_years)
        self.assertEqual(result.modified_duration, duration.modified_duration)

    def test_s16o6_reproduces_the_published_iamc_figures(self) -> None:
        result = compute_dashboard_metrics(_input())
        self.assertEqual(result.residual_days_actual, 66)  # actual days, not 30/360
        self.assertTrue(result.yield_available)
        # Published IAMC report of 10 August 2026, within display rounding.
        self.assertAlmostEqual(float(result.tna) * 100, 24.96, delta=0.1)
        self.assertAlmostEqual(float(result.tea) * 100, 28.03, delta=0.1)
        self.assertAlmostEqual(float(result.tem) * 100, 2.08, delta=0.1)
        self.assertAlmostEqual(float(result.maturity_value), 105.28, delta=0.01)


class TestTemporalAlignmentGuard(unittest.TestCase):
    """Yield metrics exist only when the price date equals the trade date."""

    def test_misaligned_price_blocks_yield_but_keeps_maturity_value(self) -> None:
        result = compute_dashboard_metrics(_input(trade_date=date(2026, 8, 12)))
        self.assertFalse(result.yield_available)
        self.assertIsNone(result.tea)
        self.assertIsNone(result.tem)
        self.assertIsNone(result.tna)
        self.assertIsNone(result.holding_period_return)
        self.assertIsNone(result.modified_duration)
        self.assertGreater(result.maturity_value, Decimal(0))
        self.assertIn("does not match", result.yield_unavailable_reason or "")

    def test_price_without_observation_date_blocks_yield(self) -> None:
        result = compute_dashboard_metrics(_input(price_date=None))
        self.assertFalse(result.yield_available)
        self.assertIn("no observation date", result.yield_unavailable_reason or "")

    def test_matured_instrument_blocks_yield(self) -> None:
        result = compute_dashboard_metrics(
            _input(
                trade_date=date(2026, 10, 16),
                price_date=date(2026, 10, 16),
                provider_settlement_date=date(2026, 10, 16),
            )
        )
        self.assertFalse(result.yield_available)
        self.assertIsNone(result.tea)


class TestSettlementDate(unittest.TestCase):
    def test_provider_settlement_is_used_when_the_price_is_aligned(self) -> None:
        result = compute_dashboard_metrics(_input())
        self.assertEqual(result.settlement_date, date(2026, 8, 11))
        self.assertEqual(result.settlement_source, "provider")

    def test_falls_back_to_next_business_day_over_a_weekend(self) -> None:
        friday = date(2026, 10, 23)
        result = compute_dashboard_metrics(
            _input(trade_date=friday, price_date=None, provider_settlement_date=None)
        )
        self.assertEqual(result.settlement_date, date(2026, 10, 26))  # Monday
        self.assertEqual(result.settlement_source, "calendar_t_plus_1")

    def test_next_business_day_skips_a_listed_holiday(self) -> None:
        # 12 October 2026 is a listed holiday.
        self.assertEqual(next_business_day(date(2026, 10, 9)), date(2026, 10, 13))

    def test_calendar_coverage_is_disclosed(self) -> None:
        result = compute_dashboard_metrics(
            _input(
                trade_date=date(2027, 6, 1),
                price_date=None,
                provider_settlement_date=None,
            )
        )
        self.assertEqual(
            result.settlement_calendar_status,
            "outside_hand_entered_calendar_coverage",
        )


class TestPayloadSerialization(unittest.TestCase):
    _FINANCIAL = (
        "maturity_value",
        "holding_period_return",
        "tea",
        "tem",
        "tna",
        "macaulay_years",
        "modified_duration",
        "periodic_yield",
    )

    def _payload(self, **overrides) -> dict:
        params = {
            "issue": "2026-07-31",
            "maturity": "2026-10-16",
            "tem": "0.0205",
            "price": "100.68",
            "trade": "2026-08-10",
            "price_date": "2026-08-10",
            "settlement": "2026-08-11",
            "type": "LECAP",
        }
        params.update(overrides)
        return metrics_payload(params)

    def test_no_financial_value_is_a_float(self) -> None:
        payload = self._payload()
        for key in self._FINANCIAL:
            with self.subTest(key=key):
                self.assertNotIsInstance(payload[key], float)
                self.assertTrue(payload[key] is None or isinstance(payload[key], str))

    def test_payload_survives_json_round_trip(self) -> None:
        payload = json.loads(json.dumps(self._payload()))
        self.assertTrue(payload["yield_available"])
        self.assertEqual(payload["residual_days_actual"], 66)
        self.assertEqual(payload["methodology"]["tea"], "R-004")

    def test_missing_parameter_is_rejected(self) -> None:
        params = {"issue": "2026-07-31"}
        with self.assertRaises(MetricsRequestError):
            metrics_payload(params)

    def test_invalid_date_is_rejected(self) -> None:
        with self.assertRaises(MetricsRequestError):
            self._payload(trade="10/08/2026")

    def test_unsupported_instrument_type_is_rejected(self) -> None:
        with self.assertRaises(MetricsRequestError):
            self._payload(type="LELINK")


class TestMetricsEndpoint(unittest.TestCase):
    """The route is read-only and never leaks internals to the browser."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.database = Path(self._tmp.name) / "market.sqlite"
        self.dashboard = Path(self._tmp.name) / "dashboard.html"
        self.dashboard.write_text("<html></html>", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _serve(self, query: str):
        server = create_server(self.dashboard, self.database, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:{}".format(server.server_address[1])
            with urlopen(base + "/api/metrics?" + query, timeout=2) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_endpoint_returns_engine_metrics(self) -> None:
        status, payload = self._serve(
            "issue=2026-07-31&maturity=2026-10-16&tem=0.0205&price=100.68"
            "&trade=2026-08-10&price_date=2026-08-10&settlement=2026-08-11"
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["yield_available"])
        self.assertEqual(payload["residual_days_actual"], 66)
        self.assertEqual(payload["settlement_source"], "provider")

    def test_endpoint_rejects_an_incomplete_request(self) -> None:
        with self.assertRaises(HTTPError) as caught:
            self._serve("issue=2026-07-31")
        self.assertEqual(caught.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
