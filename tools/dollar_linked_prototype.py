"""EXPLORATORY PROTOTYPE — Dollar-linked Treasury letras (LELINK) yields.

===============================================================================
UNVALIDATED PROTOTYPE. NOT PRODUCTION. NOT BEHIND AN APPROVED RESEARCH GATE.
===============================================================================

Research reference: docs/research/006_dollar_linked_letras.md (R-006), status
"Under Review — Implementation NOT approved".

This module is deliberately kept OUTSIDE ``src/financial_engine/`` because the
dollar-linked yield convention has NOT been validated against official sources.
It exists only to explore the calculation and render an illustrative yield curve
while R-006 is researched. Its numbers must not be quoted as validated output.

What it computes, per the R-006 working hypothesis (see that document):

    Linked leg (USD-linked unit of account):
        HPR_linked = redemption_value / market_price - 1
        D          = actual calendar days settlement -> maturity
        TEA_linked = (1 + HPR_linked)^(365 / D) - 1        # ACT/365 (hypothesis)
        TEM_linked = (1 + TEA_linked)^(1 / 12) - 1
        TNA_linked = TEM_linked * 12

    Peso leg (adds official-FX / Com. A3500 variation, a USER ASSUMPTION):
        fx_factor  = (1 + expected_annual_devaluation)^(D / 365)
        HPR_pesos  = (1 + HPR_linked) * fx_factor - 1
        TEA_pesos  = (1 + HPR_pesos)^(365 / D) - 1
        TEM_pesos  = (1 + TEA_pesos)^(1 / 12) - 1
        TNA_pesos  = TEM_pesos * 12

The linked leg mirrors the peso IAMC ACT/365 convention (R-002/R-003/R-004) as a
*starting hypothesis only*. The peso leg depends on a devaluation assumption and
inherits the open governance of R-009. Decimal only; no IO in the calc functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext

_WORKING_PRECISION = 50
_DAYS_YEAR_ACTUAL = Decimal(365)
_MONTHS_YEAR = Decimal(12)

PROTOTYPE_STATUS = (
    "UNVALIDATED PROTOTYPE — R-006 Under Review, implementation NOT approved. "
    "Linked convention is a hypothesis; peso leg depends on a devaluation "
    "assumption governed by R-009."
)


class DollarLinkedPrototypeError(Exception):
    """Base error for the dollar-linked prototype."""


class InvalidPriceError(DollarLinkedPrototypeError):
    """Market price missing or non-positive."""


class InvalidRedemptionError(DollarLinkedPrototypeError):
    """Redemption value missing or non-positive."""


class InvalidDatesError(DollarLinkedPrototypeError):
    """Settlement/maturity dates missing or inconsistent."""


@dataclass(frozen=True)
class DollarLinkedInput:
    """Immutable inputs for a single dollar-linked letra (prototype).

    Attributes:
        instrument: Human-readable instrument name (e.g. ``LELINK/U$D/30-09-2026``).
        market_price: Secondary-market price in linked units, per VN 100 (Decimal).
        settlement_date: Settlement date of the trade.
        maturity_date: Instrument maturity date.
        redemption_value: Redemption value in linked units, per VN 100. Per
            Res. Conjunta SF/SH 31/2025, LELINK are zero-coupon "a descuento",
            "íntegra al vencimiento", so redemption is par = Decimal("100"). The
            field is kept configurable only for what-if exploration; it should
            remain 100 for LELINK.
        expected_annual_devaluation: Assumed effective annual variation of the
            official exchange rate (Com. A3500) between settlement and maturity,
            as a Decimal (e.g. Decimal("0.20") = 20% p.a.). USER ASSUMPTION.
    """

    instrument: str
    market_price: Decimal
    settlement_date: date
    maturity_date: date
    redemption_value: Decimal = Decimal("100")
    expected_annual_devaluation: Decimal = Decimal("0")


@dataclass(frozen=True)
class DollarLinkedResult:
    """Immutable result for a single dollar-linked letra (prototype)."""

    instrument: str
    residual_days_actual: int
    # Linked leg (independent of any FX assumption)
    hpr_linked: Decimal
    tna_linked: Decimal
    tea_linked: Decimal
    tem_linked: Decimal
    # Peso leg (depends on the devaluation assumption)
    expected_annual_devaluation: Decimal
    fx_factor: Decimal
    hpr_pesos: Decimal
    tna_pesos: Decimal
    tea_pesos: Decimal
    tem_pesos: Decimal
    prototype_status: str = PROTOTYPE_STATUS


def _annualize(hpr: Decimal, days: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """Return (TEA, TEM, TNA) for a holding-period return over ``days`` (ACT/365).

    This is the peso IAMC convention (R-002/R-003/R-004) reused here as the R-006
    working hypothesis. Returned unrounded.
    """
    tea = (Decimal(1) + hpr) ** (_DAYS_YEAR_ACTUAL / days) - Decimal(1)
    tem = (Decimal(1) + tea) ** (Decimal(1) / _MONTHS_YEAR) - Decimal(1)
    tna = tem * _MONTHS_YEAR
    return tea, tem, tna


def calculate_dollar_linked(data: DollarLinkedInput) -> DollarLinkedResult:
    """Compute linked and peso return metrics for one dollar-linked letra.

    Raises:
        InvalidPriceError: If ``market_price`` is not positive.
        InvalidRedemptionError: If ``redemption_value`` is not positive.
        InvalidDatesError: If ``settlement_date`` is not before ``maturity_date``.
    """
    if data.market_price <= 0:
        raise InvalidPriceError("Market price must be positive.")
    if data.redemption_value <= 0:
        raise InvalidRedemptionError("Redemption value must be positive.")
    if data.settlement_date >= data.maturity_date:
        raise InvalidDatesError("Settlement date must be earlier than maturity date.")

    residual_days = (data.maturity_date - data.settlement_date).days
    if residual_days <= 0:
        raise InvalidDatesError("Residual term (actual days) must be positive.")

    with localcontext() as context:
        context.prec = _WORKING_PRECISION
        days_decimal = Decimal(residual_days)

        hpr_linked = data.redemption_value / data.market_price - Decimal(1)
        tea_linked, tem_linked, tna_linked = _annualize(hpr_linked, days_decimal)

        fx_factor = (Decimal(1) + data.expected_annual_devaluation) ** (
            days_decimal / _DAYS_YEAR_ACTUAL
        )
        hpr_pesos = (Decimal(1) + hpr_linked) * fx_factor - Decimal(1)
        tea_pesos, tem_pesos, tna_pesos = _annualize(hpr_pesos, days_decimal)

    return DollarLinkedResult(
        instrument=data.instrument,
        residual_days_actual=residual_days,
        hpr_linked=hpr_linked,
        tna_linked=tna_linked,
        tea_linked=tea_linked,
        tem_linked=tem_linked,
        expected_annual_devaluation=data.expected_annual_devaluation,
        fx_factor=fx_factor,
        hpr_pesos=hpr_pesos,
        tna_pesos=tna_pesos,
        tea_pesos=tea_pesos,
        tem_pesos=tem_pesos,
    )


def build_curve(inputs: list[DollarLinkedInput]) -> list[DollarLinkedResult]:
    """Compute results for several instruments, sorted by maturity date."""
    ordered = sorted(inputs, key=lambda d: d.maturity_date)
    return [calculate_dollar_linked(d) for d in ordered]
