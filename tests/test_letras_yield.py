"""Tests for the letras yield calculator (IAMC convention: ACT/365, TNA=TEM*12).

Anchored to the real BYMA/IAMC daily report for S16O6 (10 August 2026):
maturity value 105.28, price 100.7, settlement 2026-08-11, maturity 2026-10-16,
66 actual days. Published: HPR 4.55%, TNA 24.92%, TEA 27.97%, TEM 2.08%.

The published price (100.7) is a rounded display value, so we reproduce the
published rates within a small tolerance and additionally assert the exact
algebraic relationships that define the IAMC convention.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from financial_engine.letras_yield import (
    InvalidMaturityValueError,
    InvalidPriceError,
    InvalidYieldDatesError,
    LetraYieldInput,
    calculate_letra_yield,
)


def _s16o6():
    return LetraYieldInput(
        market_price=Decimal("100.7"),
        settlement_date=date(2026, 8, 11),
        maturity_date=date(2026, 10, 16),
        maturity_value=Decimal("105.28"),
        source_reference="BYMA/IAMC daily report 2026-08-10",
    )


def test_actual_days_matches_report():
    # IAMC prints 66 actual days for S16O6.
    assert calculate_letra_yield(_s16o6()).residual_days_actual == 66


def test_hpr_matches_report():
    result = calculate_letra_yield(_s16o6())
    assert result.holding_period_return.quantize(Decimal("0.0001")) == Decimal("0.0455")


def test_reproduces_published_iamc_rates_within_tolerance():
    result = calculate_letra_yield(_s16o6())
    # Published: TNA 24.92%, TEA 27.97%, TEM 2.08% (price display is rounded).
    assert abs(result.tna - Decimal("0.2492")) < Decimal("0.0015")
    assert abs(result.tea - Decimal("0.2797")) < Decimal("0.0015")
    assert abs(result.tem - Decimal("0.0208")) < Decimal("0.0005")


def test_tna_is_tem_times_twelve():
    # IAMC definition: TNA is the nominal annual rate compounded monthly.
    # Compared at 12 decimals to avoid decimal-context rounding noise.
    result = calculate_letra_yield(_s16o6())
    q = Decimal("0.000000000001")
    assert result.tna.quantize(q) == (result.tem * Decimal(12)).quantize(q)


def test_effective_exceeds_nominal():
    # With monthly compounding, TEA (effective) > TNA (nominal).
    result = calculate_letra_yield(_s16o6())
    assert result.tea > result.tna


def test_par_price_gives_zero_rates():
    result = calculate_letra_yield(
        LetraYieldInput(
            market_price=Decimal("100"),
            settlement_date=date(2026, 8, 11),
            maturity_date=date(2026, 10, 16),
            maturity_value=Decimal("100"),
            source_reference="par",
        )
    )
    assert result.holding_period_return == Decimal("0")
    assert result.tna == Decimal("0")
    assert result.tea == Decimal("0")
    assert result.tem == Decimal("0")


def test_invalid_price():
    with pytest.raises(InvalidPriceError):
        calculate_letra_yield(
            LetraYieldInput(
                market_price=Decimal("0"),
                settlement_date=date(2026, 8, 11),
                maturity_date=date(2026, 10, 16),
                maturity_value=Decimal("105.28"),
                source_reference="x",
            )
        )


def test_invalid_maturity_value():
    with pytest.raises(InvalidMaturityValueError):
        calculate_letra_yield(
            LetraYieldInput(
                market_price=Decimal("100.7"),
                settlement_date=date(2026, 8, 11),
                maturity_date=date(2026, 10, 16),
                maturity_value=Decimal("0"),
                source_reference="x",
            )
        )


def test_invalid_dates():
    with pytest.raises(InvalidYieldDatesError):
        calculate_letra_yield(
            LetraYieldInput(
                market_price=Decimal("100.7"),
                settlement_date=date(2026, 10, 16),
                maturity_date=date(2026, 10, 16),
                maturity_value=Decimal("105.28"),
                source_reference="x",
            )
        )


def test_reproduces_t30j7_long_instrument():
    # Second real BYMA/IAMC case (10-Aug-2026), a 323-day BONCAP where the old
    # 30/360 formula drifts ~2.6 pp: T30J7, MV 156.04, price 125.7,
    # settlement 2026-08-11, maturity 2027-06-30.
    # Published: HPR 24.13%, TNA 24.65%, TEA 27.63%, TEM 2.05%, 323 days.
    result = calculate_letra_yield(
        LetraYieldInput(
            market_price=Decimal("125.7"),
            settlement_date=date(2026, 8, 11),
            maturity_date=date(2027, 6, 30),
            maturity_value=Decimal("156.04"),
            source_reference="BYMA/IAMC daily report 2026-08-10",
        )
    )
    assert result.residual_days_actual == 323
    assert abs(result.tna - Decimal("0.2465")) < Decimal("0.0010")
    assert abs(result.tea - Decimal("0.2763")) < Decimal("0.0010")


def test_methodology_status_records_iamc_and_approval():
    status = calculate_letra_yield(_s16o6()).methodology_status
    assert "IAMC" in status
    assert "Implementation Approved" in status
