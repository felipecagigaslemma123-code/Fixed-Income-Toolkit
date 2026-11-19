"""Tests for the LECAP/BONCAP maturity value (VPV) engine (R-001).

Production implementation approved by the project owner on 2026-08-10. These
tests use exact, hand-computable cases plus the domain-exception contract.
"""
from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from financial_engine.maturity_value import (
    InstrumentType,
    InvalidFaceValueError,
    InvalidInstrumentDatesError,
    InvalidIssueRateError,
    MaturityValueInput,
    MaturityValueResult,
    calculate_maturity_value,
)


def _input(
    issue=date(2026, 1, 1),
    maturity=date(2026, 2, 1),
    rate="0.10",
    face="100",
    official="0",
) -> MaturityValueInput:
    return MaturityValueInput(
        instrument_type=InstrumentType.LECAP,
        issue_date=issue,
        maturity_date=maturity,
        monthly_issue_rate=Decimal(rate),
        reference_face_value=Decimal(face),
        official_maturity_value=Decimal(official),
        source_reference="unit-test",
    )


def test_one_conventional_month_ten_percent():
    # 30/360 term = 30 days = 1 month; 100 * 1.10^1 = 110 exactly.
    result = calculate_maturity_value(_input())
    assert isinstance(result, MaturityValueResult)
    assert result.maturity_value == Decimal("110.00")


def test_two_conventional_months():
    # 01 Jan -> 01 Mar = 60/360 = 2 months; 100 * 1.10^2 = 121 exactly.
    result = calculate_maturity_value(_input(maturity=date(2026, 3, 1)))
    assert result.maturity_value == Decimal("121.00")


def test_zero_rate_returns_face_value():
    result = calculate_maturity_value(_input(rate="0"))
    assert result.maturity_value == Decimal("100")


def test_absolute_difference_against_official():
    result = calculate_maturity_value(_input(official="110"))
    assert result.absolute_difference == Decimal("0.00")


def test_methodology_status_records_approval():
    result = calculate_maturity_value(_input())
    assert "Implementation Approved" in result.methodology_status


def test_invalid_face_value():
    with pytest.raises(InvalidFaceValueError):
        calculate_maturity_value(_input(face="0"))


def test_invalid_issue_rate():
    with pytest.raises(InvalidIssueRateError):
        calculate_maturity_value(_input(rate="-0.01"))


def test_invalid_dates():
    with pytest.raises(InvalidInstrumentDatesError):
        calculate_maturity_value(_input(issue=date(2026, 5, 1), maturity=date(2026, 5, 1)))


def test_input_is_frozen():
    data = _input()
    with pytest.raises(dataclasses.FrozenInstanceError):
        data.monthly_issue_rate = Decimal("0")  # type: ignore[misc]
