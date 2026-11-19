"""Tests for the contractual maturity registry loaded from colocaciones data."""
from __future__ import annotations

import os
from datetime import date

import pytest

from market_data.contractual import (
    ContractualMaturityRegistry,
    load_contractual_letras,
)
from market_data.models.enums import TreasuryInstrumentFamily

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_FILE = os.path.join(_REPO_ROOT, "data", "colocaciones_31-5-26.xlsx")

pytestmark = pytest.mark.skipif(
    not os.path.exists(_DATA_FILE), reason="colocaciones dataset not available"
)


def test_loads_records():
    letras = load_contractual_letras(_DATA_FILE)
    assert len(letras) > 0
    assert all(l.maturity_date is not None for l in letras)


def test_registry_has_no_conflicts_and_distinct_names():
    registry = ContractualMaturityRegistry.from_file(_DATA_FILE)
    assert registry.conflicts() == {}
    names = [l.name for l in registry.all()]
    assert len(names) == len(set(names))


def test_authoritative_maturity_lookup():
    registry = ContractualMaturityRegistry.from_file(_DATA_FILE)
    assert registry.maturity_for_name("LECAP/$/27-02-2026") == date(2026, 2, 27)
    assert registry.maturity_for_name("LECER/$/CER/29-05-2026") == date(2026, 5, 29)


def test_unknown_name_returns_none():
    registry = ContractualMaturityRegistry.from_file(_DATA_FILE)
    assert registry.maturity_for_name("NOT-A-REAL-INSTRUMENT") is None


def test_families_and_currency_inferred():
    registry = ContractualMaturityRegistry.from_file(_DATA_FILE)
    families = {l.family for l in registry.all() if l.family is not None}
    assert TreasuryInstrumentFamily.LECAP in families
    assert TreasuryInstrumentFamily.LECER in families
    # Peso instruments -> ARS; dollar-linked (U$D in the name) -> USD.
    by_name = {l.name: l for l in registry.all()}
    lecap = next(l for l in registry.all() if l.family is TreasuryInstrumentFamily.LECAP)
    assert lecap.currency == "ARS"
    dollar_linked = [l for l in registry.all() if "U$D" in l.name]
    assert dollar_linked and all(l.currency == "USD" for l in dollar_linked)
