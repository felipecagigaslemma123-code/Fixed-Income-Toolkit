"""Pure text identity helpers for Treasury/A3 instrument reconciliation.

Only information explicitly present in source text is returned. These helpers
never derive a market ticker from an instrument maturity date.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Optional

from market_data.models.enums import TreasuryInstrumentFamily

_MONTHS = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "SETIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}


def canonical_text(value: str) -> str:
    """Return uppercase, accent-free text with normalized whitespace."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.upper().split())


def normalize_ticker(value: Optional[str]) -> Optional[str]:
    """Normalize an explicit identifier without attempting to derive one."""
    if value is None:
        return None
    normalized = "".join(value.upper().split())
    return normalized or None


def normalize_a3_contract_ticker(
    value: Optional[str], term: Optional[str]
) -> Optional[str]:
    """Return the contract ticker encoded by an explicit A3 quote identity.

    A3 production observations for the 24-hour settlement term use both
    ``plazo=001`` and a ``/24hs`` suffix in ``ticker``. The raw provider ticker
    remains untouched on the quote; this helper removes only that documented,
    redundant settlement suffix when the quote itself confirms term ``001``.
    """
    ticker = normalize_ticker(value)
    normalized_term = normalize_ticker(term)
    if (
        ticker is not None
        and normalized_term == "001"
        and ticker.endswith("/24HS")
    ):
        return ticker[: -len("/24HS")] or None
    return ticker


def infer_instrument_family(text: str) -> Optional[TreasuryInstrumentFamily]:
    """Classify only when the family is explicit in the supplied text."""
    value = canonical_text(text)
    if "BONCAP" in value or (
        "BONO DEL TESORO" in value and "CAPITALIZABLE" in value
    ):
        return TreasuryInstrumentFamily.BONCAP
    if "LECAP" in value or (
        "LETRA DEL TESORO" in value and "CAPITALIZABLE" in value
    ):
        return TreasuryInstrumentFamily.LECAP
    if "LELINK" in value or "DOLAR LINKED" in value or "VINCULADA AL DOLAR" in value:
        return TreasuryInstrumentFamily.LELINK
    if "LECER" in value or "AJUSTADA POR CER" in value or "AJUSTE POR CER" in value:
        return TreasuryInstrumentFamily.LECER
    if "LEDE" in value or "A DESCUENTO" in value:
        return TreasuryInstrumentFamily.LEDE
    if "LETRA DEL TESORO" in value:
        return TreasuryInstrumentFamily.TREASURY_BILL
    if "BONO DEL TESORO" in value:
        return TreasuryInstrumentFamily.TREASURY_BOND
    return None


def infer_currency(text: str, explicit_currency: Optional[str] = None) -> Optional[str]:
    """Normalize an explicitly supplied currency code or wording."""
    if explicit_currency:
        code = canonical_text(explicit_currency)
        if code in {"$", "ARS", "PESO", "PESOS"}:
            return "ARS"
        if code in {"USD", "U$S", "US$", "DOLAR", "DOLARES"}:
            return "USD"
    value = canonical_text(text)
    if "DOLAR" in value or "USD" in value:
        return "USD"
    if "EN PESOS" in value or " ARS " in " {} ".format(value):
        return "ARS"
    return None


def parse_explicit_maturity_date(text: str) -> Optional[date]:
    """Parse a maturity date only when it is explicitly written in the text."""
    value = canonical_text(text)
    spanish = re.search(
        r"VENCIMIENTO\s+(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})", value
    )
    if spanish:
        month = _MONTHS.get(spanish.group(2))
        if month is not None:
            try:
                return date(int(spanish.group(3)), month, int(spanish.group(1)))
            except ValueError:
                return None

    numeric = re.search(
        r"(?:VTO\.?|VENCIMIENTO)?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})",
        value,
    )
    if not numeric:
        return None
    year = int(numeric.group(3))
    if year < 100:
        year += 2000
    try:
        return date(year, int(numeric.group(2)), int(numeric.group(1)))
    except ValueError:
        return None
