"""Public interface for FX forward metrics (dollar futures curve).

This module defines the *public contract* for FX forward metrics derived from a
spot exchange rate and a currency futures price: the input/output data
structures and the domain exception hierarchy. It follows the same pattern as
``maturity_value.py`` (one immutable input, one immutable result, Decimal only,
no IO).

The theoretical-parity formula is deliberately **not implemented**. The
methodology is documented in Research R-009
(``docs/research/009_forward_points_devaluation.md``), which is ``Under Review``
and has NOT been approved for production. Per the project Research First Policy,
no financial formula may be implemented before its methodology and validation
cases are documented and approved. Until then,
:func:`calculate_fx_forward_metrics` raises :class:`UnvalidatedMethodologyError`.

Scope note (terminology separation, per ``bibliography_review_2026-08-06.md``):
this module covers the **FX forward price** and forward points only. The
**forward interest rate** (candidate R-017) and the **value of an existing
forward** are distinct concepts and belong in separate modules. There is no
generic ``forward_rate`` function.

No provider is contacted, no file is read and no ``float`` is used anywhere in
this module: every financial magnitude is a :class:`decimal.Decimal`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class FxForwardMetricsError(Exception):
    """Base class for all FX forward metrics domain errors."""


class InvalidSpotError(FxForwardMetricsError):
    """Raised when the spot exchange rate is missing or non-positive."""


class InvalidFuturesPriceError(FxForwardMetricsError):
    """Raised when the futures price is missing or non-positive."""


class InvalidForwardDatesError(FxForwardMetricsError):
    """Raised when valuation/maturity dates are missing or inconsistent."""


class UnvalidatedMethodologyError(FxForwardMetricsError):
    """Raised when a calculation is requested before its methodology is validated."""


@dataclass(frozen=True)
class FxForwardMetricsInput:
    """Immutable inputs for FX forward metrics.

    Attributes:
        spot: Spot exchange rate (e.g. ARS per USD), as a Decimal. The exact
            source and quote direction are open items of R-009.
        futures_price: Observed currency futures price, as a Decimal.
        valuation_date: Date of the observation.
        maturity_date: Futures contract maturity date.
        source_reference: Human-readable citation for the observed figures.
    """

    spot: Decimal
    futures_price: Decimal
    valuation_date: date
    maturity_date: date
    source_reference: str


@dataclass(frozen=True)
class FxForwardMetricsResult:
    """Immutable result of an FX forward metrics computation.

    Attributes:
        forward_points: Observed comparison ``futures_price - spot`` (trivial
            arithmetic; does not require interest-rate curves).
        implied_devaluation: Theoretical-parity result; populated only once R-009
            is validated and approved for production.
        methodology_status: Status of the underlying methodology (R-009).
    """

    forward_points: Decimal
    implied_devaluation: Decimal
    methodology_status: str


def calculate_fx_forward_metrics(
    data: FxForwardMetricsInput,
) -> FxForwardMetricsResult:
    """Compute FX forward metrics for a dollar futures observation.

    The theoretical-parity calculation is intentionally not implemented yet.
    Research R-009 is ``Under Review``, so this function refuses to produce a
    number rather than returning an unverified result. The observed
    ``forward_points`` comparison, which needs no curves, is exposed by the
    Market Data layer as data and does not depend on this gated function.

    Args:
        data: The validated inputs describing the observation.

    Returns:
        FxForwardMetricsResult: The computed metrics (once R-009 is validated and
        implemented).

    Raises:
        UnvalidatedMethodologyError: Always, until Research R-009 is validated
            for production use.
    """
    raise UnvalidatedMethodologyError(
        "FX forward metrics are not available: Research R-009 "
        "(docs/research/009_forward_points_devaluation.md) is Under Review and "
        "has not been approved for production. No forward/futures FX formula may "
        "be implemented until the spot contract, the provider price field, the "
        "temporal policy and the ARS/USD curves are documented and approved."
    )
