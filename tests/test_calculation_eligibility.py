"""Tests for the family-based yield calculation eligibility gate."""
from __future__ import annotations

import pytest

from market_data.calculation_eligibility import (
    calculation_eligibility,
    is_yield_calculable,
)
from market_data.models.enums import TreasuryInstrumentFamily as F


@pytest.mark.parametrize("family", [F.LECAP, F.BONCAP])
def test_calculable_families(family):
    assert is_yield_calculable(family) is True
    calculable, reason = calculation_eligibility(family)
    assert calculable is True
    assert "approved" in reason.lower()


@pytest.mark.parametrize(
    "family",
    [F.LELINK, F.LECER, F.LEDE, F.TREASURY_BILL, F.TREASURY_BOND],
)
def test_non_calculable_families_have_reason(family):
    assert is_yield_calculable(family) is False
    calculable, reason = calculation_eligibility(family)
    assert calculable is False
    assert reason  # a non-empty explanation


def test_lelink_reason_mentions_dollar_link():
    _, reason = calculation_eligibility(F.LELINK)
    assert "dollar-linked" in reason.lower()


def test_lecer_reason_mentions_cer():
    _, reason = calculation_eligibility(F.LECER)
    assert "cer" in reason.lower()


def test_unknown_family_is_not_calculable():
    calculable, reason = calculation_eligibility(None)
    assert calculable is False
    assert "unknown" in reason.lower()
