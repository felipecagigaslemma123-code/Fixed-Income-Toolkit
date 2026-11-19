"""Tests for the contractual maturity resolver (explicit -> registry -> unresolved)."""
from __future__ import annotations

import os
from datetime import date

import pytest

from market_data.contractual import (
    CONTRACTUAL_UNIQUE,
    EXPLICIT,
    UNRESOLVED,
    ContractualMaturityRegistry,
    resolve_maturity,
)
from market_data.models.enums import TreasuryInstrumentFamily

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_FILE = os.path.join(_REPO_ROOT, "data", "colocaciones_31-5-26.xlsx")

pytestmark = pytest.mark.skipif(
    not os.path.exists(_DATA_FILE), reason="colocaciones dataset not available"
)


@pytest.fixture
def registry():
    return ContractualMaturityRegistry.from_file(_DATA_FILE)


def test_explicit_maturity_wins(registry):
    maturity, method = resolve_maturity(
        registry, description="anything", explicit_maturity=date(2027, 1, 1)
    )
    assert maturity == date(2027, 1, 1)
    assert method == EXPLICIT


def test_contractual_unique_match_by_name(registry):
    maturity, method = resolve_maturity(
        registry,
        description="Letra capitalizable LECAP/$/27-02-2026 en pesos",
        family=TreasuryInstrumentFamily.LECAP,
        currency="ARS",
    )
    assert maturity == date(2026, 2, 27)
    assert method == CONTRACTUAL_UNIQUE


def test_contractual_unique_match_by_date_token(registry):
    maturity, method = resolve_maturity(
        registry,
        description="LECAP en pesos con vencimiento 27-02-2026",
        family=TreasuryInstrumentFamily.LECAP,
        currency="ARS",
    )
    assert maturity == date(2026, 2, 27)
    assert method == CONTRACTUAL_UNIQUE


def test_unresolved_when_no_date_in_text(registry):
    maturity, method = resolve_maturity(
        registry,
        description="Letra del Tesoro capitalizable en pesos (sin fecha)",
        family=TreasuryInstrumentFamily.LECAP,
        currency="ARS",
    )
    assert maturity is None
    assert method == UNRESOLVED
