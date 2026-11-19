"""Tests for the single-payment letra duration engine (R-005).

Clean 90-day (30/360) case: settlement 2026-01-01, maturity 2026-04-01.
Macaulay = 90/360 = 0.25 years. With TEA = 0.25 and annual frequency (m=1):
Modified = 0.25 / 1.25 = 0.20 exactly.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from financial_engine.duration import (
    DurationInput,
    InvalidDurationDatesError,
    InvalidFrequencyError,
    InvalidYieldInputError,
    calculate_duration,
)


def _input(settlement=date(2026, 1, 1), maturity=date(2026, 4, 1), tea="0.25", m=1):
    return DurationInput(
        settlement_date=settlement,
        maturity_date=maturity,
        tea=Decimal(tea),
        compounding_frequency=m,
        source_reference="unit-test",
    )


def test_macaulay_years_and_days():
    result = calculate_duration(_input())
    assert result.macaulay_days_30_360 == 90
    assert result.macaulay_years == Decimal("0.25")


def test_modified_annual_frequency_exact():
    result = calculate_duration(_input(tea="0.25", m=1))
    # periodic_yield = TEA (m=1); Modified = 0.25 / 1.25 = 0.20.
    assert result.periodic_yield == Decimal("0.25")
    assert result.modified_duration == Decimal("0.20")


def test_modified_less_than_macaulay_for_positive_yield():
    result = calculate_duration(_input(tea="0.30", m=12))
    assert result.modified_duration < result.macaulay_years
    assert result.compounding_frequency == 12


def test_zero_yield_makes_modified_equal_macaulay():
    result = calculate_duration(_input(tea="0", m=1))
    assert result.modified_duration == result.macaulay_years


def test_invalid_dates():
    with pytest.raises(InvalidDurationDatesError):
        calculate_duration(_input(settlement=date(2026, 4, 1), maturity=date(2026, 4, 1)))


def test_invalid_tea():
    with pytest.raises(InvalidYieldInputError):
        calculate_duration(_input(tea="-1"))


def test_invalid_frequency():
    with pytest.raises(InvalidFrequencyError):
        calculate_duration(_input(m=0))


def test_methodology_status_records_approval():
    assert "Implementation Approved" in calculate_duration(_input()).methodology_status
