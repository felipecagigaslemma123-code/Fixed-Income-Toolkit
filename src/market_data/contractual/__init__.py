"""Contractual reference data for Treasury instruments.

Separate from market data: this package reads *contractual* facts (issuance,
maturity) from official Treasury issuance datasets. It is the authoritative
source of an instrument's maturity date, used so that instrument desenlace
(maturity) never depends on scraping free text.
"""

from __future__ import annotations

from market_data.contractual.colocaciones import (
    ContractualLetra,
    ContractualMaturityRegistry,
    load_contractual_letras,
)
from market_data.contractual.maturity_resolver import (
    CONTRACTUAL_UNIQUE,
    EXPLICIT,
    UNRESOLVED,
    resolve_maturity,
)

__all__ = [
    "ContractualLetra",
    "ContractualMaturityRegistry",
    "load_contractual_letras",
    "resolve_maturity",
    "EXPLICIT",
    "CONTRACTUAL_UNIQUE",
    "UNRESOLVED",
]
