"""Stage 0 tests for the gated FX forward metrics engine module.

These tests exercise ONLY the public contract: imports, dataclass immutability,
the domain-exception hierarchy, and the research-gate guard. No financial
calculation is implemented yet (Research R-009 is Under Review).
"""
from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from financial_engine.fx_forward_metrics import (
    FxForwardMetricsError,
    FxForwardMetricsInput,
    FxForwardMetricsResult,
    InvalidForwardDatesError,
    InvalidFuturesPriceError,
    InvalidSpotError,
    UnvalidatedMethodologyError,
    calculate_fx_forward_metrics,
)


def _sample_input() -> FxForwardMetricsInput:
    return FxForwardMetricsInput(
        spot=Decimal("1400.00"),
        futures_price=Decimal("1450.50"),
        valuation_date=date(2026, 8, 6),
        maturity_date=date(2026, 8, 31),
        source_reference="unit-test placeholder",
    )


def test_input_is_frozen_and_decimal():
    data = _sample_input()
    assert isinstance(data.spot, Decimal)
    assert isinstance(data.futures_price, Decimal)
    with pytest.raises(dataclasses.FrozenInstanceError):
        data.spot = Decimal("0")  # type: ignore[misc]


def test_result_dataclass_shape():
    result = FxForwardMetricsResult(
        forward_points=Decimal("50.50"),
        implied_devaluation=Decimal("0"),
        methodology_status="UNDER_REVIEW",
    )
    assert result.forward_points == Decimal("50.50")


def test_calculation_is_gated():
    with pytest.raises(UnvalidatedMethodologyError):
        calculate_fx_forward_metrics(_sample_input())


def test_exception_hierarchy():
    assert issubclass(UnvalidatedMethodologyError, FxForwardMetricsError)
    assert issubclass(InvalidSpotError, FxForwardMetricsError)
    assert issubclass(InvalidFuturesPriceError, FxForwardMetricsError)
    assert issubclass(InvalidForwardDatesError, FxForwardMetricsError)
