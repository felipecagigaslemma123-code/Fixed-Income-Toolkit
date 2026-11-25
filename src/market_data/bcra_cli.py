"""Descarga una muestra de CER, TAMAR privada TNA y A3500 del BCRA."""

import argparse
from pathlib import Path
import sys

from .providers.bcra import BCRAError, extract, save_capture
from financial_engine._common import parse_bcra_date


def main(argumentos=None, *, fetch=None, project_root):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desde", required=True, help="Primera fecha de referencia, inclusive (AAAA-MM-DD).")
    parser.add_argument("--hasta", required=True, help="Última fecha de referencia, inclusive (AAAA-MM-DD).")
    parser.add_argument("--salida", required=True, type=Path, help="Archivo JSON nuevo fuera del proyecto.")
    opciones = parser.parse_args(argumentos)
    try:
        destino = opciones.salida.expanduser()
        destino = destino.parent.resolve() / destino.name
        proyecto = Path(project_root).resolve()
        if destino == proyecto or proyecto in destino.parents:
            raise BCRAError("Elegí un archivo de salida fuera del proyecto.")
        if destino.exists() or destino.is_symlink():
            raise BCRAError("El archivo de salida ya existe. Elegí otro para conservar la captura.")
        datos = extract(parse_bcra_date(opciones.desde), parse_bcra_date(opciones.hasta), fetch=fetch)
        save_capture(datos, destino)
    except (BCRAError, OSError) as error:
        print("BCRA: {}".format(error), file=sys.stderr)
        return 1
    print("Muestra del BCRA guardada en {}.".format(destino))
    for clave, serie in datos["series"].items():
        observaciones = serie["observaciones"]
        if observaciones:
            print("{} · {} observaciones · última fecha {}".format(
                clave, len(observaciones), observaciones[-1]["fecha"]))
        else:
            print("{} · sin dato en el rango consultado".format(clave))
    return 0

