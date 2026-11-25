"""Shared validation and Decimal helpers, moved without changing messages or precision."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from functools import wraps
import re

from .indexed_types import BCRAError


class FinancialInputError(ValueError):
    """Datos de letras inválidos; no se sustituyen por valores supuestos."""

    def __init__(self, errores):
        self.errores = [errores] if isinstance(errores, str) else list(errores)
        super().__init__("\n".join(self.errores))


def parse_date(valor, campo):
    if isinstance(valor, datetime):
        raise FinancialInputError("{} debe ser una fecha sin hora.".format(campo))
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        try:
            return date.fromisoformat(valor)
        except ValueError:
            pass
    raise FinancialInputError("{} inválida; usá AAAA-MM-DD.".format(campo))


def parse_decimal(valor, campo, cero=False):
    if isinstance(valor, bool) or not isinstance(valor, (str, int, float, Decimal)):
        raise FinancialInputError("{} debe ser un número finito {}.".format(campo, "no negativo" if cero else "positivo"))
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise FinancialInputError("{} inválido; usá punto decimal y sin separadores de miles.".format(campo))
    if not numero.is_finite() or numero < 0 or not cero and numero == 0:
        raise FinancialInputError("{} debe ser un número finito {}.".format(campo, "no negativo" if cero else "positivo"))
    return numero


def decimal_text(valor):
    return format(valor, "f")


def _precision(funcion):
    @wraps(funcion)
    def calcular(*args, **kwargs):
        with localcontext() as contexto:
            contexto.prec = 50
            return funcion(*args, **kwargs)
    return calcular


def _mes(fecha, desplazamiento=0):
    anio, mes = divmod(fecha.year * 12 + fecha.month - 1 + desplazamiento, 12)
    return date(anio, mes + 1, 1)


def _distancia_meses(a, b):
    return (b.year - a.year) * 12 + b.month - a.month


def parse_bcra_date(texto):
    try:
        fecha = date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise BCRAError("Fecha inválida, se espera AAAA-MM-DD.") from None
    if fecha.isoformat() != texto:
        raise BCRAError("Fecha inválida, se espera AAAA-MM-DD.")
    return fecha

