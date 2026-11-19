"""Start the public DLR observer and its local Chrome dashboard together."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start observed dollar futures locally (no credentials)."
    )
    parser.add_argument(
        "--database",
        default="data/market/market_data.sqlite",
        help="Shared local SQLite database path.",
    )
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-open-chrome", action="store_true")
    return parser.parse_args()


def _observer_command(args: argparse.Namespace) -> List[str]:
    return [
        sys.executable,
        str(_REPO_ROOT / "tools" / "run_futures_scheduler.py"),
        "--database",
        args.database,
    ]


def _dashboard_command(args: argparse.Namespace) -> List[str]:
    command = [
        sys.executable,
        str(_REPO_ROOT / "tools" / "serve_local_dashboard.py"),
        "--database",
        args.database,
        "--port",
        str(args.port),
        "--page",
        "futures",
    ]
    if args.no_open_chrome:
        command.append("--no-open-chrome")
    return command


def _stop(process: Optional[subprocess.Popen[bytes]]) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    args = _arguments()
    if sys.version_info < (3, 9):
        print("ERROR: Fixed Income Toolkit requires Python 3.9 or newer.")
        return 2

    observer: Optional[subprocess.Popen[bytes]] = None
    dashboard: Optional[subprocess.Popen[bytes]] = None
    try:
        observer = subprocess.Popen(_observer_command(args), cwd=str(_REPO_ROOT))
        dashboard = subprocess.Popen(_dashboard_command(args), cwd=str(_REPO_ROOT))
        print(
            "Futuros DLR iniciados en esta computadora (fuente pública provisoria).",
            flush=True,
        )
        while dashboard.poll() is None:
            if observer is not None and observer.poll() is not None:
                print(
                    "El observador se detuvo; la pantalla continúa con los "
                    "datos ya guardados.",
                    flush=True,
                )
                observer = None
            time.sleep(1)
        return dashboard.returncode or 0
    except KeyboardInterrupt:
        print("Cerrando futuros DLR locales.", flush=True)
        return 0
    finally:
        _stop(dashboard)
        _stop(observer)


if __name__ == "__main__":
    raise SystemExit(main())
