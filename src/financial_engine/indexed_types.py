"""Shared index data types; legacy field names preserve the Cartera contract."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class BCRAError(ValueError):
    """Respuesta inválida del BCRA o imposibilidad de completar la captura."""


@dataclass(frozen=True)
class RemSurvey:
    mes: date
    ipc: dict[date, Decimal]
    ipc_12m: Decimal
    ipc_24m: Decimal
    tamar: dict[date, Decimal]
    tamar_12m: Decimal
    tc: dict[date, Decimal]
    tc_12m: Decimal


@dataclass(frozen=True)
class IndexedValue:
    valor: Decimal
    origen: str

