"""Ejecuta una consulta autenticada de solo lectura a BYMA Market Data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from market_data.models.exceptions import MarketDataError  # noqa: E402
from market_data.providers.byma import BYMA_OPERATIONS, BymaMarketDataClient  # noqa: E402


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=BYMA_OPERATIONS)
    parser.add_argument("--param", action="append", default=[], metavar="NOMBRE=VALOR")
    parser.add_argument("--raw", action="store_true", help="Escribe la respuesta original en stdout.")
    args = parser.parse_args(argv)

    parameters = {}
    for item in args.param:
        key, separator, value = item.partition("=")
        if not separator or not key or not value or key in parameters:
            parser.error("Usá --param NOMBRE=VALOR una sola vez por parámetro.")
        parameters[key] = value

    try:
        response = BymaMarketDataClient().fetch(args.operation, parameters)
    except MarketDataError as exc:
        print(f"BYMA {args.operation}: {exc}", file=sys.stderr)
        return 1

    print(
        f"BYMA {args.operation}: {response.format}, {len(response.body)} bytes, "
        f"recibidos {response.received_at.isoformat()}",
        file=sys.stderr if args.raw else sys.stdout,
    )
    if args.raw:
        sys.stdout.buffer.write(response.body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
