"""BCRA public-series transport, validated capture persistence and REM Excel reader."""

from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from openpyxl import load_workbook

from financial_engine._common import _precision, _mes, parse_bcra_date
from financial_engine.indexed_types import BCRAError, RemSurvey

URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
SERIES = {"cer": 30, "tamar_tna": 44, "a3500": 5}
_IDENTIDAD = {
    "cer": ("Coeficiente de estabilización de referencia (base 2.2.02=1)", "Índice base 2.2.02=1"),
    "tamar_tna": ("Tasa de interes TAMAR de bancos privados", "En porcentaje nominal anual"),
    "a3500": ("Tipo de cambio mayorista de referencia", "Pesos argentinos por dólar estadounidense"),
}
_LIMITE = 1000
_MAX_BYTES = 2_000_000


def _descargar(url):
    solicitud = Request(url, headers={"Accept": "application/json", "Accept-Language": "es-AR",
                                     "Accept-Encoding": "identity", "User-Agent": "cartera-bcra/0.1"})
    with urlopen(solicitud, timeout=10) as respuesta:
        return respuesta.read(_MAX_BYTES + 1)


def _pagina(url, fetch, offset):
    try:
        cuerpo = fetch(url)
        if not isinstance(cuerpo, bytes) or len(cuerpo) > _MAX_BYTES:
            raise ValueError("respuesta fuera del formato o tamaño esperado")
        pagina = json.loads(cuerpo, parse_float=Decimal, parse_constant=Decimal)
        if not isinstance(pagina, dict) or pagina.get("status") != 200:
            raise ValueError("la API no informó un estado 200")
        resultados = pagina["results"]
        datos = pagina["metadata"]["resultset"]
        cantidad, limite = datos["count"], datos["limit"]
        if (not isinstance(resultados, list) or type(cantidad) is not int or cantidad < offset
                or type(limite) is not int or limite <= 0 or datos.get("offset") != offset
                or any(not isinstance(fila, dict) for fila in resultados)):
            raise ValueError("paginación o resultados inválidos")
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        raise BCRAError("No se pudo leer {}. {}".format(url, error)) from None
    return resultados, cantidad, limite


def _catalogo(clave, id_variable, fetch):
    url = URL + "?" + urlencode({"idVariable": id_variable, "limit": 1, "offset": 0})
    filas, cantidad, _ = _pagina(url, fetch, 0)
    if cantidad != 1 or len(filas) != 1 or filas[0].get("idVariable") != id_variable:
        raise BCRAError("{}: la serie {} no se encontró en el catálogo.".format(clave, id_variable))
    fila = filas[0]
    nombre, unidad = _IDENTIDAD[clave]
    descripcion = fila.get("descripcion")
    if (not isinstance(descripcion, str) or " ".join(descripcion.split()).casefold() != nombre.casefold()
            or fila.get("periodicidad") != "D" or fila.get("categoria") != "Principales Variables"
            or fila.get("unidadExpresion") != unidad):
        raise BCRAError("{}: la descripción, frecuencia o unidad de la serie {} cambió.".format(clave, id_variable))
    return fila


def _observaciones(id_variable, desde, hasta, fetch):
    consulta = "{}/{}?{}".format(URL, id_variable, urlencode({"desde": desde, "hasta": hasta}))
    valores = {}
    cantidad = None
    while True:
        offset = len(valores)
        url = "{}&limit={}&offset={}".format(consulta, _LIMITE, offset)
        filas, total, limite = _pagina(url, fetch, offset)
        if cantidad is None:
            cantidad = total
        detalle = filas[0].get("detalle") if len(filas) == 1 and filas[0].get("idVariable") == id_variable else None
        if (total != cantidad or total > (hasta - desde).days + 1 or not isinstance(detalle, list)
                or len(detalle) != min(limite, total - offset)):
            raise BCRAError("Serie {}: detalle o paginación incoherente.".format(id_variable))
        for registro in detalle:
            if not isinstance(registro, dict):
                raise BCRAError("Serie {}: observación inválida.".format(id_variable))
            fecha, valor = parse_bcra_date(registro.get("fecha")), registro.get("valor")
            if fecha in valores or not desde <= fecha <= hasta:
                raise BCRAError("Serie {}: fecha duplicada o fuera de rango, {}.".format(id_variable, fecha))
            if type(valor) not in (int, Decimal) or not Decimal(valor).is_finite():
                raise BCRAError("Serie {}: valor no numérico o no finito en {}.".format(id_variable, fecha))
            valores[fecha] = str(valor)
        if len(valores) == cantidad:
            break
    return [{"fecha": fecha.isoformat(), "valor": valores[fecha]} for fecha in sorted(valores)]


def extract(desde, hasta, *, fetch=None, hasta_cer=None):
    """Devuelve una captura fechada con la serie publicada y su procedencia."""
    if type(desde) is not date or type(hasta) is not date or desde > hasta:
        raise BCRAError("El rango debe tener dos fechas válidas, desde ≤ hasta.")
    if hasta_cer is not None and (type(hasta_cer) is not date or hasta_cer < hasta):
        raise BCRAError("El límite de CER debe ser igual o posterior al fin del rango general.")
    fetch = _descargar if fetch is None else fetch
    series = {}
    for clave, id_variable in SERIES.items():
        metadatos = _catalogo(clave, id_variable, fetch)
        fin = hasta_cer if clave == "cer" and hasta_cer is not None else hasta
        observaciones = _observaciones(id_variable, desde, fin, fetch)
        series[clave] = {"id_variable": id_variable, "url": "{}/{}".format(URL, id_variable),
                         "descripcion": metadatos["descripcion"].strip(), "unidad": metadatos["unidadExpresion"],
                         "periodicidad": metadatos["periodicidad"],
                         "primera_fecha_catalogo": metadatos.get("primerFechaInformada"),
                         "ultima_fecha_catalogo": metadatos.get("ultFechaInformada"),
                         "estado": "publicado" if observaciones else "sin dato", "observaciones": observaciones}
        if fin != hasta:
            series[clave]["hasta_consultado"] = fin.isoformat()
    return {"esquema_version": 1, "fuente": "BCRA",
            "consultado_en": datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).isoformat(),
            "desde": desde.isoformat(), "hasta": hasta.isoformat(), "series": series}


def save_capture(datos, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=destino.parent, delete=False) as archivo:
            temporal = Path(archivo.name)
            json.dump(datos, archivo, ensure_ascii=False, indent=2, allow_nan=False)
            archivo.write("\n")
        os.link(temporal, destino)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


@_precision
def read_rem(ruta):
    """Lee las medianas de la hoja oficial, sin depender del nombre del archivo."""
    encabezados = {
        "Precios minoristas (IPC nivel general-Nacional; INDEC)": ("ipc", "var. % mensual", 100),
        "Tasa de interés (TAMAR)": ("tamar", "TNA; %", 100),
        "Tipo de cambio nominal": ("tc", "$/USD", 1),
    }
    series = {nombre: {} for nombre, _, _ in encabezados.values()}
    horizontes = {}
    bloque = None
    libro = load_workbook(ruta, read_only=True, data_only=True)
    try:
        for _, periodo, referencia, mediana in libro["Cuadros de resultados"].iter_rows(
            max_col=4, values_only=True
        ):
            if periodo in encabezados:
                bloque = encabezados[periodo]
                continue
            if periodo is None:
                bloque = None
            if bloque is None or mediana is None:
                continue
            nombre, unidad, escala = bloque
            if isinstance(periodo, date) and referencia == unidad:
                destino, clave = series[nombre], _mes(periodo)
            elif periodo == "próx. 12 meses" or (periodo == "próx. 24 meses" and nombre == "ipc"):
                destino, clave = horizontes, (nombre, periodo)
            else:
                continue
            if clave in destino or type(mediana) not in (float, int, Decimal):
                raise ValueError("Mediana inválida o duplicada en el REM.")
            valor = Decimal(str(mediana)) / escala
            if not valor.is_finite():
                raise ValueError("Mediana no finita en el REM.")
            destino[clave] = valor
    finally:
        libro.close()
    try:
        return RemSurvey(min(series["ipc"]), series["ipc"], horizontes["ipc", "próx. 12 meses"],
                   horizontes["ipc", "próx. 24 meses"], series["tamar"],
                   horizontes["tamar", "próx. 12 meses"], series["tc"],
                   horizontes["tc", "próx. 12 meses"])
    except (KeyError, ValueError):
        raise ValueError("El REM no contiene las medianas requeridas.") from None

