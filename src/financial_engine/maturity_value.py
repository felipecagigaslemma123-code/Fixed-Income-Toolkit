"""Public interface for the LECAP/BONCAP maturity value module.

This module defines the *public contract* for computing the maturity value of
Argentine capitalizable Treasury Bills (LECAP) and capitalizable Treasury Bonds
(BONCAP): the input/output data structures, the instrument taxonomy and the
domain exception hierarchy.

The maturity value formula is implemented under the validated and owner-
approved Research R-001 methodology (production approval dated 10 August
2026). The historical :class:`UnvalidatedMethodologyError` remains part of the
public exception hierarchy for compatibility and future independently gated
methodologies; this approved calculation does not raise it.

No Excel files are read, no external APIs are contacted, and no ``float`` values
are used anywhere in this module: every financial magnitude is a
:class:`decimal.Decimal`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from enum import Enum

from financial_engine.day_count import days_30_360_treasury

# High working precision for intermediate compounding; results are not rounded
# for presentation (financial_specification.md numerical-accuracy rule).
_WORKING_PRECISION = 50

# Methodology status recorded on every result (owner-approved production use).
_METHODOLOGY_STATUS = "R-001 Validated — Implementation Approved (owner, 2026-08-10)"


class InstrumentType(Enum):
    """Supported capitalizable fixed-income instrument types.

    Attributes:
        LECAP: Argentine capitalizable Treasury Bill (Letra Capitalizable).
        BONCAP: Argentine capitalizable Treasury Bond (Bono Capitalizable).
    """

    LECAP = "LECAP"
    BONCAP = "BONCAP"


class MaturityValueError(Exception):
    """Base class for all maturity value domain errors."""


class InvalidFaceValueError(MaturityValueError):
    """Raised when a reference face value is missing or non-positive."""


class InvalidIssueRateError(MaturityValueError):
    """Raised when the monthly issue rate is missing or out of range."""


class InvalidInstrumentDatesError(MaturityValueError):
    """Raised when issue/maturity dates are missing or inconsistent."""


class UnvalidatedMethodologyError(MaturityValueError):
    """Raised while the methodology's production Research Gate remains closed."""


@dataclass(frozen=True)
class MaturityValueInput:
    """Immutable inputs required to compute an instrument's maturity value.

    Attributes:
        instrument_type: The capitalizable instrument family (LECAP or BONCAP).
        issue_date: The instrument's issue date.
        maturity_date: The instrument's maturity date.
        monthly_issue_rate: Monthly issue (capitalization) rate, as a Decimal.
        reference_face_value: Reference face value per unit, as a Decimal.
        official_maturity_value: Official maturity value published by the source,
            retained for validation/comparison, as a Decimal.
        source_reference: Human-readable citation for the official figures
            (e.g. official report or validation case identifier).
    """

    instrument_type: InstrumentType
    issue_date: date
    maturity_date: date
    monthly_issue_rate: Decimal
    reference_face_value: Decimal
    official_maturity_value: Decimal
    source_reference: str


@dataclass(frozen=True)
class MaturityValueResult:
    """Immutable result of a maturity value computation.

    Attributes:
        maturity_value: The computed maturity value, as a Decimal.
        reference_face_value: The reference face value used, as a Decimal.
        official_maturity_value: The official maturity value for comparison,
            as a Decimal.
        absolute_difference: Absolute difference between the computed and
            official maturity values, as a Decimal.
        methodology_status: Status of the underlying methodology (e.g. the
            validation state of Research R-001).
    """

    maturity_value: Decimal
    reference_face_value: Decimal
    official_maturity_value: Decimal
    absolute_difference: Decimal
    methodology_status: str


def calculate_maturity_value(
    data: MaturityValueInput,
) -> MaturityValueResult:
    """Compute the maturity value (VPV) for a LECAP/BONCAP instrument.

    Applies the Research R-001 methodology, approved for production by the
    project owner on 2026-08-10:

        capitalization_months = DAYS360_TREASURY(issue_date, maturity_date) / 30
        maturity_value = reference_face_value
                         * (1 + monthly_issue_rate) ** capitalization_months

    The Treasury-adapted 30/360 day count is documented in
    ``docs/market_conventions.md``. Intermediate values are not rounded.

    Args:
        data: The validated inputs describing the instrument.

    Returns:
        MaturityValueResult: The computed maturity value and its comparison
        against the source-published figure.

    Raises:
        InvalidFaceValueError: If the reference face value is not positive.
        InvalidIssueRateError: If the monthly issue rate is negative.
        InvalidInstrumentDatesError: If the issue date is not before maturity.
    """
    if data.reference_face_value <= 0:
        raise InvalidFaceValueError("Reference face value must be positive.")
    if data.monthly_issue_rate < 0:
        raise InvalidIssueRateError("Monthly issue rate must be non-negative.")
    if data.issue_date >= data.maturity_date:
        raise InvalidInstrumentDatesError(
            "Issue date must be earlier than maturity date."
        )

    with localcontext() as context:
        context.prec = _WORKING_PRECISION
        months = Decimal(days_30_360_treasury(data.issue_date, data.maturity_date))
        capitalization_months = months / Decimal(30)
        growth = (Decimal(1) + data.monthly_issue_rate) ** capitalization_months
        maturity_value = data.reference_face_value * growth
        absolute_difference = abs(maturity_value - data.official_maturity_value)

    return MaturityValueResult(
        maturity_value=maturity_value,
        reference_face_value=data.reference_face_value,
        official_maturity_value=data.official_maturity_value,
        absolute_difference=absolute_difference,
        methodology_status=_METHODOLOGY_STATUS,
    )
