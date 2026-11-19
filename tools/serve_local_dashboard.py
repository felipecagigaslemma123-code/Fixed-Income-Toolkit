"""Serve the approved Toolkit dashboard locally and open it in Google Chrome."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from local_dashboard.server import create_server  # noqa: E402
from market_data.config.settings import StorageConfig  # noqa: E402

_DASHBOARD_PATH = _REPO_ROOT / "outputs" / "modelo_lecap_boncap.html"
_FUTURES_DASHBOARD_PATH = _REPO_ROOT / "outputs" / "futuros_dolar.html"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve the Toolkit dashboards on this computer only."
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--page",
        choices=("letras", "futures"),
        default="letras",
        help="Page Google Chrome opens first.",
    )
    parser.add_argument(
        "--database",
        default=StorageConfig().database_path,
        help="SQLite market-data path.",
    )
    parser.add_argument(
        "--no-open-chrome",
        action="store_true",
        help="Start the local page without opening Google Chrome.",
    )
    return parser.parse_args()


def _open_chrome(url: str) -> None:
    try:
        subprocess.Popen(
            ["open", "-a", "Google Chrome", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        print("Google Chrome could not be opened automatically: {}".format(exc))


def main() -> int:
    args = _arguments()
    database_path = Path(args.database)
    if not database_path.is_absolute():
        database_path = _REPO_ROOT / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)

    server = create_server(
        _DASHBOARD_PATH,
        database_path,
        port=args.port,
        futures_dashboard_path=_FUTURES_DASHBOARD_PATH,
    )
    host, port = server.server_address
    suffix = "/futures" if args.page == "futures" else ""
    url = "http://{}:{}{}".format(host, port, suffix)
    print("Dashboard local disponible en {}".format(url), flush=True)
    print("Cerrar con Control+C.", flush=True)
    if not args.no_open_chrome:
        _open_chrome(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Dashboard local detenido.", flush=True)
        return 0
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
