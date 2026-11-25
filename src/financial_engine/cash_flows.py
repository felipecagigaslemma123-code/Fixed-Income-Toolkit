"""IAMC schedules and ACT/365 purchase yield, without customer holdings or files.

Dates, schemas, Decimal arithmetic, notices and legacy dataclass fields are
preserved from Cartera. Indexed flows require explicit approved contract inputs.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, DecimalException, localcontext
from typing import List, Optional

from ._common import parse_decimal, parse_date

_FIJA = "fix"
_TOLERANCIA = Decimal("0.01")

@dataclass
class Payment:
    fecha: date
    amortizacion: Decimal
    renta: Decimal
    origen: str
    dual: Optional[tuple] = None

    @property
    def total(self):
        return self.amortizacion + self.renta


@dataclass
class CashFlowSchedule:
    ticker: str
    grupo: str
    familia: str
    moneda: str
    plaza: str
    habilitado: bool
    fecha_cierre: date
    liquidacion: date
    pagos: List[Payment]


@dataclass
class PurchaseSchedule:
    pagos: List[Payment]
    completo: bool
    faltante_desde: Optional[date]
    faltante_hasta: Optional[date]
    advertencias: List[str]


def _fecha_cierre(cierre):
    if not isinstance(cierre, dict):
        raise ValueError("Cada cierre de IAMC debe ser un objeto.")
    return parse_date(cierre.get("fecha_cierre"), "Fecha del cierre IAMC")


def _fecha_a3500_iamc(cierre, fecha_cierre):
    """Fecha del A3500 con que IAMC expresa los flujos dólar linked de ese cierre."""
    variables = (cierre.get("macro") or {}).get("vars") if isinstance(cierre.get("macro"), dict) else None
    for variable in variables or ():
        if isinstance(variable, dict) and variable.get("k") == "a3500":
            return parse_date(variable.get("f"), "Fecha del A3500 de IAMC")
    return fecha_cierre


def iamc_schedule(cierre, ticker, grupo, *, contrato=None, indices=None, avisos=None):
    """Lee pagos por 100 nominales originales del registro exacto de calculadora."""
    fecha_cierre = _fecha_cierre(cierre)
    calculadora = cierre.get("calculadora_bonos")
    if not isinstance(calculadora, dict) or not isinstance(calculadora.get("ins"), list):
        raise ValueError("El cierre IAMC carece de calculadora_bonos.ins.")
    if any(not isinstance(registro, dict) for registro in calculadora["ins"]):
        raise ValueError("El cierre IAMC contiene registros de instrumentos inválidos.")
    registros = [fila for fila in calculadora["ins"] if fila.get("tk") == ticker and fila.get("g") == grupo]
    if not registros:
        return None
    if len(registros) != 1:
        raise ValueError("{} {}: registros duplicados en IAMC al {}.".format(ticker, grupo, fecha_cierre))
    fila = registros[0]
    familia, moneda, plaza = (fila.get(campo) for campo in ("k", "cur", "fxr"))
    liquidacion = parse_date(fila.get("liq"), "Liquidación IAMC")
    habilitado = familia == _FIJA
    pagos = {}
    if contrato is not None and indices is not None and familia in ("cer", "dl", "var", "capv"):
        from .indexed_payments import project_indexed_payments
        # IAMC expresa los flujos dólar linked al A3500 de su bloque macro, que puede
        # ser anterior a la fecha del cierre (el 12/11/2026 usó el del 11/11).
        fila = dict(fila, _fecha_a3500_iamc=_fecha_a3500_iamc(cierre, fecha_cierre))
        pagos = {fecha: Payment(fecha, amortizacion, renta, origen, dual)
                 for fecha, amortizacion, renta, origen, dual in project_indexed_payments(
                     fila, contrato, fecha_cierre, liquidacion, indices, avisos)}
        habilitado, moneda, plaza = True, "ARS", "ARS"
    elif habilitado:
        if moneda not in ("ARS", "USD") or moneda == "USD" and plaza not in ("MEP", "CCL"):
            raise ValueError("{}: moneda o plaza inválida para un flujo de tasa fija.".format(ticker))
        if not isinstance(fila.get("f"), list):
            raise ValueError("{}: falta el flujo de calculadora IAMC.".format(ticker))
        for registro in fila["f"]:
            if not isinstance(registro, (list, tuple)) or len(registro) != 4:
                raise ValueError("{}: pago inválido en la calculadora IAMC.".format(ticker))
            dias = parse_decimal(registro[0], "Días del pago IAMC", cero=True)
            if dias != dias.to_integral_value() or dias > (date.max - liquidacion).days:
                raise ValueError("{}: fecha inválida en el flujo IAMC.".format(ticker))
            fecha = liquidacion + timedelta(days=int(dias))
            if fecha in pagos:
                raise ValueError("{}: pago duplicado en IAMC el {}.".format(ticker, fecha))
            pagos[fecha] = Payment(fecha, parse_decimal(registro[1], "Amortización", cero=True),
                               parse_decimal(registro[2], "Renta", cero=True), "iamc " + fecha_cierre.isoformat())
    return CashFlowSchedule(ticker, grupo, familia, moneda, plaza, habilitado, fecha_cierre, liquidacion,
                      [pagos[fecha] for fecha in sorted(pagos)])


def _serie(cierres, ticker, grupo, *, contrato=None, indices=None, avisos=None):
    serie = []
    for cierre in sorted(cierres, key=_fecha_cierre):
        try:
            cronograma = iamc_schedule(cierre, ticker, grupo, contrato=contrato, indices=indices, avisos=avisos)
        except (ValueError, DecimalException, KeyError, TypeError) as error:
            if contrato is None or cierre is max(cierres, key=_fecha_cierre):
                raise
            avisos.append("Cierre IAMC del {} sin proyección: {}.".format(_fecha_cierre(cierre), error))
            cronograma = None
        if cronograma is None:
            liquidacion = parse_date(cierre.get("fecha_liquidacion"), "Liquidación del cierre IAMC")
            serie.append((liquidacion, {}, None))
        else:
            serie.append((cronograma.liquidacion, {pago.fecha: pago for pago in cronograma.pagos}, cronograma))
    return serie


def _manuales(registros):
    pagos = {}
    for fila in registros:
        if not isinstance(fila, (list, tuple)) or len(fila) != 3:
            raise ValueError("Cada pago manual requiere fecha, amortización y renta.")
        fecha = parse_date(fila[0], "Fecha del pago manual")
        if fecha in pagos:
            raise ValueError("Pago manual duplicado el {}.".format(fecha))
        pagos[fecha] = Payment(fecha, parse_decimal(fila[1], "Amortización manual", cero=True),
                           parse_decimal(fila[2], "Renta manual", cero=True), "manual")
    return pagos


def _fusionar_pagos(serie, manuales):
    if not serie or serie[-1][2] is None or not serie[-1][2].habilitado:
        return {}, None, []
    vigente = serie[-1][2]
    # Moneda y plaza del instrumento actual también gobiernan qué datos son comparables.
    fuentes = [(liq, pagos, c) for liq, pagos, c in serie
               if c is not None and c.habilitado and (c.moneda, c.plaza) == (vigente.moneda, vigente.plaza)]
    primera_liq = min(liq for liq, _, _ in fuentes)
    fechas = {fecha for _, pagos, _ in fuentes for fecha in pagos}
    seleccion, avisos = {}, []
    for fecha in sorted(fechas):
        for liq, pagos, cierre in reversed(serie):
            if liq >= fecha:
                continue
            if (cierre is not None and cierre.habilitado
                    and (cierre.moneda, cierre.plaza) == (vigente.moneda, vigente.plaza)
                    and fecha in pagos):
                seleccion[fecha] = pagos[fecha]
            else:
                avisos.append("Pago del {} ausente del último cierre aplicable: posible reprogramación.".format(fecha))
            break
    if manuales is not None:
        for fecha, manual in manuales.items():
            pago = seleccion.get(fecha)
            if pago is not None:
                if (abs(pago.amortizacion - manual.amortizacion) > _TOLERANCIA
                        or abs(pago.renta - manual.renta) > _TOLERANCIA):
                    avisos.append("{}: pago manual (amortización {}, renta {}) difiere de IAMC "
                                  "(amortización {}, renta {}). Se usa IAMC.".format(
                                      fecha, manual.amortizacion, manual.renta, pago.amortizacion, pago.renta))
            elif fecha <= primera_liq:
                seleccion[fecha] = manual
        amortizado = sum((p.amortizacion for p in seleccion.values()), Decimal(0))
        if abs(amortizado - 100) > _TOLERANCIA:
            avisos.append("El cronograma con pagos manuales suma {} de amortización por 100 VN y no 100: "
                          "falta cargar pagos del prospecto o hay un importe mal cargado.".format(amortizado))
    return seleccion, primera_liq, avisos


def _para_compra(seleccion, primera_liq, avisos, liquidacion, tiene_manuales):
    pagos = [seleccion[fecha] for fecha in sorted(seleccion) if fecha > liquidacion]
    falta = primera_liq is None or liquidacion < primera_liq and not tiene_manuales
    return PurchaseSchedule(pagos, not falta, liquidacion if falta else None,
                            primera_liq if falta else None, list(avisos))


def purchase_schedule(cierres, ticker, grupo, liquidacion, pagos_manuales=None):
    """Combina cierres para recuperar los pagos posteriores a la liquidación."""
    liquidacion = parse_date(liquidacion, "Liquidación de la compra")
    manuales = None if pagos_manuales is None else _manuales(pagos_manuales)
    seleccion, primera_liq, avisos = _fusionar_pagos(_serie(cierres, ticker, grupo), manuales)
    return _para_compra(seleccion, primera_liq, avisos, liquidacion, manuales is not None)


def purchase_yield(precio, liquidacion, pagos):
    """Resuelve la TIR ACT/365 con el flujo contractual por 100 VN."""
    try:
        precio = parse_decimal(precio, "Precio de compra")
        liquidacion = parse_date(liquidacion, "Liquidación de la compra")
        with localcontext() as contexto:
            contexto.prec = 50
            flujos = [(pago.total, Decimal((pago.fecha - liquidacion).days) / 365)
                      for pago in pagos if pago.fecha > liquidacion]
            if not flujos or any(total < 0 or not total.is_finite() for total, _ in flujos):
                return None

            def diferencia(tasa):
                return sum((total / (1 + tasa) ** plazo for total, plazo in flujos), Decimal(0)) - precio

            inferior, superior = Decimal("-0.99"), Decimal(10)
            if diferencia(inferior) <= 0 or diferencia(superior) >= 0:
                return None
            for _ in range(180):
                media = (inferior + superior) / 2
                residuo = diferencia(media)
                if abs(residuo) < Decimal("1e-10"):
                    return media
                if residuo > 0:
                    inferior = media
                else:
                    superior = media
    except (ValueError, DecimalException):
        return None
    return None

