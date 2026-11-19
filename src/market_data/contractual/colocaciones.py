"""Load Treasury issuance ("Colocaciones") datasets as contractual reference data.

Reads the ``Letras`` sheet of the official ``colocaciones_*.xlsx`` files and
produces immutable :class:`ContractualLetra` records. The maturity date is taken
from the sheet's authoritative ``Vencimiento`` column — never inferred from a
ticker or from free text.

Only the standard library plus ``openpyxl`` (already a project dependency) is
used. This module performs no market-data access and no financial calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Optional, Tuple

from market_data.instrument_identity import canonical_text, infer_instrument_family
from market_data.models.enums import TreasuryInstrumentFamily
from market_data.models.exceptions import NormalizationError

_SHEET_NAME = "Letras"
_NAME_HEADER = "NOMBRE DEL INSTRUMENTO"
_MATURITY_HEADER = "VENCIMIENTO"
_ISSUE_HEADER = "FECHA DE EMISION"
_RESOLUTION_HEADER = "RESOLUCION"


@dataclass(frozen=True)
class ContractualLetra:
    """One issued Treasury bill, as recorded in the official issuance dataset.

    Attributes:
        name: Contractual instrument name (e.g. ``LECAP/$/27-02-2026``).
        family: Instrument family inferred from explicit wording in the name.
        currency: ``"ARS"`` or ``"USD"`` inferred from the name, or ``None``.
        issue_date: Issue date, if present.
        maturity_date: Authoritative maturity date (from the ``Vencimiento``
            column).
        resolution: Auction resolution reference, if present.
        source_file: The dataset file the record was read from.
    """

    name: str
    family: Optional[TreasuryInstrumentFamily]
    currency: Optional[str]
    issue_date: Optional[date]
    maturity_date: date
    resolution: Optional[str]
    source_file: str


def _as_date(value: object) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _infer_currency(name: str) -> Optional[str]:
    value = canonical_text(name)
    if "U$D" in value or "USD" in value:
        return "USD"
    if "$" in name:
        return "ARS"
    return None


def _header_index(row: Tuple, wanted: str) -> Optional[int]:
    for index, cell in enumerate(row):
        if cell is not None and canonical_text(str(cell)) == wanted:
            return index
    return None


def load_contractual_letras(path: str) -> Tuple[ContractualLetra, ...]:
    """Read the ``Letras`` sheet of a Colocaciones workbook.

    Args:
        path: Filesystem path to a ``colocaciones_*.xlsx`` file.

    Returns:
        The contractual bill records, in sheet order.

    Raises:
        NormalizationError: If the sheet or its expected columns are not found.
    """
    import openpyxl  # local import; only needed when actually loading a file

    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises various IO/format errors
        raise NormalizationError(
            "Cannot open colocaciones workbook: {}".format(exc)
        ) from exc

    if _SHEET_NAME not in workbook.sheetnames:
        raise NormalizationError(
            "Colocaciones workbook has no '{}' sheet".format(_SHEET_NAME)
        )
    sheet = workbook[_SHEET_NAME]

    rows = list(sheet.iter_rows(values_only=True))
    header_row = None
    header_index = None
    for index, row in enumerate(rows):
        if _header_index(row, _NAME_HEADER) is not None and (
            _header_index(row, _MATURITY_HEADER) is not None
        ):
            header_row = row
            header_index = index
            break
    if header_row is None or header_index is None:
        raise NormalizationError("Colocaciones 'Letras' sheet has no header row")

    name_col = _header_index(header_row, _NAME_HEADER)
    maturity_col = _header_index(header_row, _MATURITY_HEADER)
    issue_col = _header_index(header_row, _ISSUE_HEADER)
    resolution_col = _header_index(header_row, _RESOLUTION_HEADER)

    records = []
    for row in rows[header_index + 1 :]:
        if name_col >= len(row) or maturity_col >= len(row):
            continue
        raw_name = row[name_col]
        maturity = _as_date(row[maturity_col])
        if not raw_name or maturity is None:
            continue
        name = str(raw_name).strip()
        if not name:
            continue
        records.append(
            ContractualLetra(
                name=name,
                family=infer_instrument_family(name),
                currency=_infer_currency(name),
                issue_date=_as_date(row[issue_col]) if issue_col is not None else None,
                maturity_date=maturity,
                resolution=(
                    str(row[resolution_col]).strip()
                    if resolution_col is not None
                    and resolution_col < len(row)
                    and row[resolution_col] is not None
                    else None
                ),
                source_file=path,
            )
        )
    return tuple(records)


class ContractualMaturityRegistry:
    """Authoritative maturity lookup built from contractual issuance records.

    The registry deduplicates by instrument name (an instrument may be issued in
    several tranches/reopenings). If the same name ever carried inconsistent
    maturities, that is surfaced rather than silently resolved.
    """

    def __init__(self, letras: Tuple[ContractualLetra, ...]):
        self._by_name: Dict[str, ContractualLetra] = {}
        self._conflicts: Dict[str, set] = {}
        for letra in letras:
            existing = self._by_name.get(letra.name)
            if existing is None:
                self._by_name[letra.name] = letra
            elif existing.maturity_date != letra.maturity_date:
                self._conflicts.setdefault(letra.name, {existing.maturity_date})
                self._conflicts[letra.name].add(letra.maturity_date)

    @classmethod
    def from_file(cls, path: str) -> "ContractualMaturityRegistry":
        """Build a registry from a colocaciones workbook path."""
        return cls(load_contractual_letras(path))

    def maturity_for_name(self, name: str) -> Optional[date]:
        """Return the maturity date for a contractual instrument name, or None."""
        record = self._by_name.get(name.strip())
        return None if record is None else record.maturity_date

    def all(self) -> Tuple[ContractualLetra, ...]:
        """Return all distinct instruments, ordered by name."""
        return tuple(self._by_name[name] for name in sorted(self._by_name))

    def conflicts(self) -> Dict[str, set]:
        """Return names that carried inconsistent maturities (should be empty)."""
        return dict(self._conflicts)
