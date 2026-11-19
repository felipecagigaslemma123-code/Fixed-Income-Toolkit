"""Resolve an instrument's maturity from explicit data or the contractual registry.

Priority (most reliable first):

1. an explicit maturity already parsed from the source;
2. an unambiguous match against the authoritative contractual registry
   (``ContractualMaturityRegistry``);
3. otherwise ``None`` with method ``"unresolved"`` — the caller must surface the
   instrument as maturity-unknown instead of leaving it silently active forever.

This module never infers a maturity from a ticker.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

from market_data.contractual.colocaciones import ContractualMaturityRegistry
from market_data.instrument_identity import canonical_text
from market_data.models.enums import TreasuryInstrumentFamily

# Resolution methods, for traceability in the caller.
EXPLICIT = "explicit"
CONTRACTUAL_UNIQUE = "contractual-unique"
UNRESOLVED = "unresolved"


def _date_tokens(day: date) -> Tuple[str, ...]:
    return (
        "{:02d}-{:02d}-{:04d}".format(day.day, day.month, day.year),
        "{:02d}/{:02d}/{:04d}".format(day.day, day.month, day.year),
    )


def resolve_maturity(
    registry: ContractualMaturityRegistry,
    description: str,
    family: Optional[TreasuryInstrumentFamily] = None,
    currency: Optional[str] = None,
    explicit_maturity: Optional[date] = None,
) -> Tuple[Optional[date], str]:
    """Resolve a maturity date and report how it was resolved.

    Args:
        registry: The authoritative contractual maturity registry.
        description: Free-text instrument description from the source.
        family: Instrument family, if known (narrows the match).
        currency: Currency (``"ARS"``/``"USD"``), if known (narrows the match).
        explicit_maturity: A maturity already parsed from the source, if any.

    Returns:
        A ``(maturity_date, method)`` tuple. ``method`` is one of ``EXPLICIT``,
        ``CONTRACTUAL_UNIQUE`` or ``UNRESOLVED``. ``maturity_date`` is ``None``
        only when ``method`` is ``UNRESOLVED``.
    """
    if explicit_maturity is not None:
        return explicit_maturity, EXPLICIT

    canon = canonical_text(description)
    matched_dates = set()
    for record in registry.all():
        if family is not None and record.family is not family:
            continue
        if (
            currency is not None
            and record.currency is not None
            and record.currency != currency
        ):
            continue
        if canonical_text(record.name) in canon or any(
            token in canon for token in _date_tokens(record.maturity_date)
        ):
            matched_dates.add(record.maturity_date)

    if len(matched_dates) == 1:
        return next(iter(matched_dates)), CONTRACTUAL_UNIQUE
    return None, UNRESOLVED
