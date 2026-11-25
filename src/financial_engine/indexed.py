"""CER, TAMAR and A3500 curves (R-010/R-011/R-012); Decimal operations unchanged."""

from datetime import timedelta
from decimal import Decimal, ROUND_CEILING

from ._common import _precision, _mes, _distancia_meses, parse_bcra_date
from .indexed_types import BCRAError, IndexedValue

@_precision
def bcra_series(captura, clave):
    observaciones = captura["series"][clave]["observaciones"]
    escala = 100 if clave == "tamar_tna" else 1
    serie = {}
    for observacion in observaciones:
        fecha = parse_bcra_date(observacion["fecha"])
        valor = Decimal(observacion["valor"]) / escala
        if fecha in serie or not valor.is_finite():
            raise BCRAError("Observación inválida o duplicada en {}.".format(clave))
        serie[fecha] = valor
    return serie


@_precision
def monthly_inflation(rem, hasta):
    meses = [_mes(rem.mes, i) for i in range(1, 13)]
    producto = Decimal(1)
    faltantes = 0
    for mes in meses:
        if mes in rem.ipc:
            producto *= 1 + rem.ipc[mes]
        else:
            faltantes += 1
    tasa_complementaria = ((1 + rem.ipc_12m) / producto) ** (Decimal(1) / faltantes) - 1 if faltantes else None
    tasa_segundo_anio = (1 + rem.ipc_24m) ** (Decimal(1) / 12) - 1
    resultado = {}
    for distancia in range(_distancia_meses(rem.mes, hasta) + 1):
        mes = _mes(rem.mes, distancia)
        if mes in rem.ipc:
            resultado[mes] = rem.ipc[mes]
        elif distancia:
            resultado[mes] = tasa_complementaria if distancia <= 12 else tasa_segundo_anio
        else:
            raise ValueError("Falta la mediana de IPC del mes relevado.")
    return resultado


def _publicado(serie, fecha):
    anterior = max((dia for dia in serie if dia <= fecha), default=None)
    if anterior is None:
        raise ValueError("No hay observaciones publicadas al {}.".format(fecha))
    return anterior, IndexedValue(serie[anterior], "publicado")


def _geometrica(a, b, desde, hasta, fecha):
    return a * (b / a) ** (Decimal((fecha - desde).days) / (hasta - desde).days)


@_precision
def cer_index(publicado, inflacion, fecha):
    desde, ultimo = _publicado(publicado, fecha)
    if fecha <= max(publicado):
        return ultimo
    valor = ultimo.valor
    origen = "proyectado"
    while desde < fecha:
        fin = desde.replace(day=15) if desde.day < 15 else _mes(desde, 1).replace(day=15)
        objetivo = min(fin, fecha)
        if desde.day != 15:
            anterior, previo = _publicado(publicado, desde - timedelta(days=1))
            tasa = (valor / previo.valor) ** (Decimal(1) / (desde - anterior).days)
            valor *= tasa ** (objetivo - desde).days
        else:
            mes = _mes(desde, -1)
            if mes not in inflacion:
                raise ValueError("Falta la inflación de {} para proyectar CER.".format(mes))
            tasa = inflacion[mes]
            if isinstance(tasa, IndexedValue):
                if tasa.origen == "manual":
                    origen = "manual"
                tasa = tasa.valor
            valor *= (1 + tasa) ** (Decimal((objetivo - desde).days) / (fin - desde).days)
        desde = objetivo
    return IndexedValue(valor, origen)


@_precision
def a3500_index(publicado, rem, fecha):
    desde, ultimo = _publicado(publicado, fecha)
    if fecha <= max(publicado):
        return ultimo
    puntos_rem = {_mes(rem.mes, 12): rem.tc_12m, **rem.tc}
    puntos = [(desde, ultimo)]
    for mes, valor in sorted(puntos_rem.items()):
        dia = mes.replace(day=15)
        if dia > desde:
            puntos.append((dia, valor if isinstance(valor, IndexedValue) else IndexedValue(valor, "proyectado")))
    if len(puntos) < 2:
        raise ValueError("Faltan referencias futuras de A3500 en el REM.")
    for (inicio, a), (fin, b) in zip(puntos, puntos[1:]):
        if fecha <= fin:
            if fecha == fin:
                return b
            break
    origen = "manual" if "manual" in (a.origen, b.origen) else "proyectado"
    return IndexedValue(_geometrica(a.valor, b.valor, inicio, fin, fecha), origen)


@_precision
def daily_tamar(publicado, rem, fecha):
    if publicado and fecha <= max(publicado):
        return _publicado(publicado, fecha)[1]
    mes = _mes(fecha)
    puntos = {_mes(rem.mes, 12): rem.tamar_12m, **rem.tamar}
    if mes in puntos:
        valor = puntos[mes]
        return valor if isinstance(valor, IndexedValue) else IndexedValue(valor, "proyectado")
    anteriores = [dia for dia in puntos if dia < mes]
    if not anteriores:
        raise ValueError("Falta TAMAR del REM para {}.".format(mes))
    inicio = max(anteriores)
    a = puntos[inicio]
    a = a if isinstance(a, IndexedValue) else IndexedValue(a, "proyectado")
    fin = min((dia for dia in puntos if dia > mes), default=None)
    if fin is None:
        return a
    b = puntos[fin]
    b = b if isinstance(b, IndexedValue) else IndexedValue(b, "proyectado")
    fraccion = Decimal(_distancia_meses(inicio, mes)) / _distancia_meses(inicio, fin)
    origen = "manual" if "manual" in (a.origen, b.origen) else "proyectado"
    return IndexedValue(a.valor + (b.valor - a.valor) * fraccion, origen)


@_precision
def tamar_monthly_rate(tna, margen):
    return (1 + (tna + margen) * 32 / 365) ** (Decimal(365) / 384) - 1


@_precision
def project_capitalizing(mv, tem, n, me, tems):
    restantes = n - me
    if restantes < 0:
        raise ValueError("Los meses transcurridos superan el plazo del título.")
    cantidad = int(restantes.to_integral_value(rounding=ROUND_CEILING))
    if len(tems) < cantidad:
        raise ValueError("Faltan TEM para proyectar el pago capitalizable.")
    for k in range(cantidad):
        mv *= ((1 + tems[k]) / (1 + tem)) ** min(Decimal(1), restantes - k)
    return mv

