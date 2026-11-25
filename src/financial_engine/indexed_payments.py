"""Proyección de cronogramas indexados con los datos contractuales de cada especie."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING

from .indexed import (_mes, _precision, _publicado, a3500_index, cer_index,
                      monthly_inflation, project_capitalizing, daily_tamar, tamar_monthly_rate)
from ._common import parse_decimal, parse_date


def _referencia(fecha, rezago, feriados, avisos):
    if type(rezago) is not int or rezago < 0:
        raise ValueError("Falta un rezago contractual válido en días hábiles.")
    while rezago:
        fecha -= timedelta(days=1)
        anio = str(fecha.year)
        if anio not in feriados:
            aviso = "días hábiles sin feriados de " + anio
            if aviso not in avisos:
                avisos.append(aviso)
        if fecha.weekday() < 5 and fecha not in feriados.get(anio, ()):
            rezago -= 1
    return fecha


def _origen(valores):
    origenes = {valor.origen for valor in valores}
    if "manual" in origenes:
        return "manual"
    if "proyectado" in origenes:
        return "proyectado"
    return "publicado"


def _etiqueta(origen, rem):
    if origen == "manual":
        return "estimado · supuesto manual"
    if origen == "proyectado":
        return "estimado · REM " + rem.mes.isoformat()[:7]
    return "definitivo · BCRA publicado"


def _cer(indices, fecha):
    publicados, rem = indices["cer"], indices["rem"]
    inflacion = {}
    if publicados and fecha > max(publicados) and rem is not None:
        inflacion = monthly_inflation(rem, _mes(fecha))
    inflacion.update(indices["inflacion"])
    return cer_index(publicados, inflacion, fecha)


def _dolar(indices, fecha):
    publicado, rem = indices["a3500"], indices["rem"]
    if publicado and fecha <= max(publicado):
        return _publicado(publicado, fecha)[1]
    if rem is None:
        mes = _mes(fecha)
        manual = indices["tc"].get(mes)
        if manual is not None and fecha == mes.replace(day=15):
            return manual
        raise ValueError("Falta el REM para proyectar A3500.")
    return a3500_index(publicado, replace(rem, tc={**rem.tc, **indices["tc"]}), fecha)


def _tamar(indices, fecha):
    publicado, rem = indices["tamar_tna"], indices["rem"]
    if publicado and fecha <= max(publicado):
        return _publicado(publicado, fecha)[1]
    mes = _mes(fecha)
    if mes in indices["tamar"]:
        return indices["tamar"][mes]
    if rem is None:
        raise ValueError("Falta el REM para proyectar TAMAR.")
    return daily_tamar(publicado, rem, fecha)


def _ventana_tamar(indices, inicio, fin):
    """TAMAR diaria de los días hábiles de [inicio, fin): publicada si hay dato, si no proyectada.

    Dentro del tramo publicado solo cuentan los días con dato del BCRA, como en los avisos de pago
    (verificado con los 12 cupones de BAM27 y RVS1O de 2025 y 2026).
    """
    publicado, feriados = indices["tamar_tna"], indices["feriados"]
    ultimo = max(publicado) if publicado else None
    valores, dia = [], inicio
    while dia < fin:
        if ultimo is not None and dia <= ultimo:
            if dia in publicado:
                valores.append(_publicado(publicado, dia)[1])
        elif dia.weekday() < 5 and dia not in feriados.get(str(dia.year), ()):
            valores.append(_tamar(indices, dia))
        dia += timedelta(days=1)
    if not valores:
        raise ValueError("El período del cupón TAMAR no tiene días hábiles.")
    return valores


def _tasa(valor):
    tasa = Decimal(str(valor))
    if not tasa.is_finite():
        raise ValueError("Falta una tasa finita en el registro IAMC.")
    return tasa


def _cer_real(contrato, registros):
    reales = contrato.get("pagos_reales")
    if reales is None:
        if len(registros) == 1 and registros[0][2][2] == 0:
            return {registros[0][0]: (Decimal(100), Decimal(0))}
        raise ValueError("Faltan los pagos reales por 100 VN en el contrato CER.")
    resultado = {}
    for fecha, amortizacion, renta in reales:
        fecha = parse_date(fecha, "Fecha del flujo real")
        if fecha in resultado:
            raise ValueError("Pago real CER duplicado en {}.".format(fecha))
        resultado[fecha] = (parse_decimal(amortizacion, "Amortización real", cero=True),
                            parse_decimal(renta, "Renta real", cero=True))
    return resultado


def _capitalizable(fila, liquidacion, fecha, indices, referencia):
    capitalizacion = fila["c"]
    patas = {pata["k"]: pata for pata in capitalizacion["patas"]}
    if set(patas) not in ({"TAMAR"}, {"TAMAR", "DL"}) or len(patas) != len(capitalizacion["patas"]):
        raise ValueError("Índice sin fuente para las patas de la capitalización.")
    pata = patas["TAMAR"]
    n, me = (parse_decimal(capitalizacion[clave], clave, cero=True) for clave in ("n", "me"))
    meses = int((n - me).to_integral_value(rounding=ROUND_CEILING))
    tasas = [_tamar(indices, _mes(liquidacion, k)) for k in range(meses)]
    tems = [tamar_monthly_rate(v.valor, _tasa(pata["m"])) for v in tasas]
    tamar = project_capitalizing(parse_decimal(pata["mv"], "mv"), _tasa(pata["tem"]), n, me, tems)
    if "DL" not in patas:
        return tamar, _origen(tasas), None
    cambio = _dolar(indices, referencia(fecha))
    base = _publicado(indices["a3500"], fila.get("_fecha_a3500_iamc") or fila["fecha_cierre"])[1].valor
    dolar = parse_decimal(patas["DL"]["mv"], "mv dólar") * cambio.valor / base
    fxc = parse_decimal(fila["fxc"], "A3500 inicial IAMC")
    regla = capitalizacion["regla"]
    if regla not in ("MIN", "MAX"):
        raise ValueError("Regla dual desconocida.")
    ganador = (min if regla == "MIN" else max)(tamar, dolar)
    pata_ganadora = "empate" if tamar == dolar else ("TAMAR" if ganador == tamar else "A3500")
    return ganador * fxc, _origen([*tasas, cambio]), (pata_ganadora, abs(tamar - dolar) * fxc)


@_precision
def project_indexed_payments(fila, contrato, cierre, liquidacion, indices, avisos):
    familia = fila["k"]
    tipo = contrato.get("tipo")
    if not isinstance(contrato.get("fuente"), str) or not contrato["fuente"].strip():
        raise ValueError("Falta la fuente contractual del índice.")
    if familia == "var" and fila.get("v", {}).get("idx") != "TAMAR":
        raise ValueError("Índice sin fuente.")
    if not ((familia, tipo) in (("cer", "CER"), ("dl", "A3500"), ("var", "TAMAR"))
            or familia == "capv" and tipo in ("TAMAR", "A3500", "DUAL")):
        raise ValueError("El índice contractual no corresponde a la familia IAMC.")
    registros = []
    for registro in fila["f"]:
        if not isinstance(registro, (list, tuple)) or len(registro) != 4:
            raise ValueError("Pago inválido en la calculadora IAMC.")
        desplazamiento = parse_decimal(registro[0], "Días del pago IAMC", cero=True)
        if desplazamiento != desplazamiento.to_integral_value() or desplazamiento > (date.max - liquidacion).days:
            raise ValueError("Fecha inválida en el flujo IAMC.")
        registros.append((liquidacion + timedelta(days=int(desplazamiento)), desplazamiento, registro))
    registros.sort(key=lambda registro: registro[0])
    if len({fecha for fecha, _, _ in registros}) != len(registros):
        raise ValueError("Hay fechas repetidas en el flujo IAMC.")
    rezago = contrato.get("rezago_habiles")

    def referencia(fecha):
        return _referencia(fecha, rezago, indices["feriados"], avisos)

    reales = _cer_real(contrato, registros) if familia == "cer" else {}
    if familia == "cer":
        inicial = parse_decimal(contrato.get("valor_inicial"), "CER inicial")
    if familia == "dl":
        fxc = parse_decimal(fila["fxc"], "A3500 inicial IAMC")
        a3500_iamc = _publicado(indices["a3500"], fila.get("_fecha_a3500_iamc") or cierre)[1].valor
        if "valor_inicial" in contrato and abs(parse_decimal(contrato["valor_inicial"], "A3500 inicial") - fxc) > Decimal("0.0001"):
            avisos.append("revisar valor inicial del A3500")
    pagos = []
    for j, (fecha, _, registro) in enumerate(registros):
        amortizacion = parse_decimal(registro[1], "Amortización IAMC", cero=True)
        renta = parse_decimal(registro[2], "Renta IAMC", cero=True)
        dual = None
        if familia == "dl":
            valor = _dolar(indices, referencia(fecha))
            factor = fxc * valor.valor / a3500_iamc
            amortizacion, renta = amortizacion * factor, renta * factor
            origen = valor.origen
        elif familia == "cer":
            if fecha not in reales:
                raise ValueError("Falta el flujo real del {}.".format(fecha))
            real_amort, real_renta = reales[fecha]
            if real_amort + real_renta:
                # IAMC expresa el flujo CER al CER de la liquidación del cierre menos el mismo
                # rezago contractual (verificado al centésimo de pb con X29E7 y X30N6).
                cer_iamc = (amortizacion + renta) / (real_amort + real_renta) * inicial
                cer_control = _cer(indices, referencia(liquidacion)).valor
                if abs(cer_iamc / cer_control - 1) > Decimal("0.0001"):
                    aviso = ("revisar valor inicial del CER: con {} el flujo de IAMC implica un CER de {} y el "
                             "publicado para {} es {}").format(inicial, cer_iamc.quantize(Decimal("0.0001")),
                                                             referencia(liquidacion),
                                                             cer_control.quantize(Decimal("0.0001")))
                    # Un solo aviso por valor inicial: queda el del cierre más reciente.
                    prefijo = "revisar valor inicial del CER: con {} ".format(inicial)
                    avisos[:] = [a for a in avisos if not a.startswith(prefijo)]
                    avisos.append(aviso)
            valor = _cer(indices, referencia(fecha))
            amortizacion, renta = real_amort * valor.valor / inicial, real_renta * valor.valor / inicial
            origen = valor.origen
        elif familia == "var":
            base = parse_decimal(registro[3], "Base del cupón", cero=True)
            if j:
                anterior = registros[j - 1][0]
            else:
                # El cupón en curso empieza en el último pago cargado del prospecto.
                anterior = max((dia for dia in contrato.get("_pagos_previos", ()) if dia < fecha), default=None)
            if anterior is None:
                renta = base * _tasa(fila["v"]["vig"])
                pagos.append((fecha, amortizacion, renta, "definitivo · IAMC publicado", None))
                continue
            valores = _ventana_tamar(indices, referencia(anterior), referencia(fecha))
            tasa = sum(v.valor for v in valores) / len(valores) + _tasa(fila["v"]["m"])
            if contrato.get("piso") is not None:
                tasa = max(tasa, _tasa(contrato["piso"]))
            renta = base * tasa
            origen = _origen(valores)
        else:
            if len(registros) != 1:
                raise ValueError("Se esperaba un único pago capitalizable.")
            amortizacion, origen, dual = _capitalizable(
                {**fila, "fecha_cierre": cierre}, liquidacion, fecha, indices, referencia)
            renta = Decimal(0)
        etiqueta = _etiqueta(origen, indices["rem"])
        if familia == "cer" and origen != "publicado":
            etiqueta += " · CER publicado hasta " + max(indices["cer"]).isoformat()
        pagos.append((fecha, amortizacion, renta, etiqueta, dual))
    return pagos
