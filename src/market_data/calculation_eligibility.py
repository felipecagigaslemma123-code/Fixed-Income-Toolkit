"""Whether an instrument's yield is calculable, by family (governance gate).

Separates **universe visibility** (an instrument can be discovered by the
Treasury and be active in the secondary market) from **calculation eligibility**
(whether the Toolkit has an approved yield methodology for its family).

Only LECAP and BONCAP (fixed-rate capitalizable) have a validated,
implementation-approved yield methodology (R-001, R-002, R-003, R-004). Other
families are visible but explicitly **not calculated**, with a reason, so the
Toolkit never invents a rate using a convention that does not apply:

- LELINK (dollar-linked): maturity value depends on the USD adjustment;
- LECER (CER-adjusted): maturity value depends on the CER coefficient;
- LEDE (discount): outside the approved LECAP/BONCAP scope;
- generic Treasury bill/bond or unknown: family not specifically supported.

This module is pure: no IO, no financial calculation.
"""

from __future__ import annotations

from typing import Optional, Tuple

from market_data.models.enums import TreasuryInstrumentFamily

# Families whose yield methodology is validated AND implementation-approved.
_CALCULABLE_FAMILIES = frozenset(
    {TreasuryInstrumentFamily.LECAP, TreasuryInstrumentFamily.BONCAP}
)

_CALCULABLE_REASON = (
    "LECAP/BONCAP fixed-rate capitalizable: yield methodology approved "
    "(R-001, R-002, R-003, R-004)."
)

_NOT_CALCULABLE_REASON = {
    TreasuryInstrumentFamily.LELINK: (
        "Dollar-linked: maturity value depends on the USD adjustment; no "
        "approved yield methodology."
    ),
    TreasuryInstrumentFamily.LECER: (
        "CER-adjusted: maturity value depends on the CER coefficient; no "
        "approved yield methodology."
    ),
    TreasuryInstrumentFamily.LEDE: (
        "Discount bill: outside the approved LECAP/BONCAP methodology scope."
    ),
    TreasuryInstrumentFamily.TREASURY_BILL: (
        "Generic Treasury bill: family not specifically classified; no approved "
        "yield methodology."
    ),
    TreasuryInstrumentFamily.TREASURY_BOND: (
        "Generic Treasury bond: family not specifically classified; no approved "
        "yield methodology."
    ),
}

_UNKNOWN_REASON = "Unknown family: not classified from the source wording."


def is_yield_calculable(family: Optional[TreasuryInstrumentFamily]) -> bool:
    """Return ``True`` only for families with an approved yield methodology."""
    return family in _CALCULABLE_FAMILIES


def calculation_eligibility(
    family: Optional[TreasuryInstrumentFamily],
) -> Tuple[bool, str]:
    """Return ``(calculable, reason)`` for an instrument family.

    Args:
        family: The instrument family, or ``None`` if it could not be classified.

    Returns:
        A ``(calculable, reason)`` tuple. ``calculable`` is ``True`` only for
        LECAP/BONCAP; otherwise ``False`` with an explanatory reason.
    """
    if family in _CALCULABLE_FAMILIES:
        return True, _CALCULABLE_REASON
    if family is None:
        return False, _UNKNOWN_REASON
    return False, _NOT_CALCULABLE_REASON.get(
        family, "Family without an approved yield methodology."
    )
