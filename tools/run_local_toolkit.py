"""Start the local data scheduler and approved HTML dashboard together."""

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
        description="Start local Treasury/A3 updates and the Chrome dashboard."
    )
    parser.add_argument("--environment", choices=("UAT", "PROD"), default="UAT")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required safety acknowledgement for production.",
    )
    parser.add_argument(
        "--database",
        default="data/market/market_data.sqlite",
        help="Shared SQLite database path.",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--max-result-articles", type=int, default=None)
    parser.add_argument("--no-open-chrome", action="store_true")
    parser.add_argument(
        "--external-scheduler",
        action="store_true",
        help="Serve the dashboard without starting a duplicate data scheduler.",
    )
    return parser.parse_args()


def _scheduler_command(args: argparse.Namespace) -> List[str]:
    command = [
        sys.executable,
        str(_REPO_ROOT / "tools" / "run_treasury_bill_scheduler.py"),
        "--environment",
        args.environment,
        "--database",
        args.database,
    ]
    if args.allow_production:
        command.append("--allow-production")
    if args.max_result_articles is not None:
        command.extend(["--max-result-articles", str(args.max_result_articles)])
    return command


def _dashboard_command(args: argparse.Namespace) -> List[str]:
    command = [
        sys.executable,
        str(_REPO_ROOT / "tools" / "serve_local_dashboard.py"),
        "--database",
        args.database,
        "--port",
        str(args.port),
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
    if args.environment == "PROD" and not args.allow_production:
        print("ERROR: production requires the explicit --allow-production flag")
        return 2
    if args.max_result_articles is not None and args.max_result_articles < 1:
        print("ERROR: --max-result-articles must be at least 1")
        return 2

    scheduler: Optional[subprocess.Popen[bytes]] = None
    dashboard: Optional[subprocess.Popen[bytes]] = None
    try:
        if not args.external_scheduler:
            scheduler = subprocess.Popen(
                _scheduler_command(args), cwd=str(_REPO_ROOT)
            )
        dashboard = subprocess.Popen(_dashboard_command(args), cwd=str(_REPO_ROOT))
        print("Fixed Income Toolkit local iniciado ({}).".format(args.environment))
        while dashboard.poll() is None:
            if scheduler is not None and scheduler.poll() is not None:
                print(
                    "El actualizador se detuvo; el dashboard continúa con los "
                    "datos ya guardados."
                )
                scheduler = None
            time.sleep(1)
        return dashboard.returncode or 0
    except KeyboardInterrupt:
        print("Cerrando Fixed Income Toolkit local.")
        return 0
    finally:
        _stop(dashboard)
        _stop(scheduler)


if __name__ == "__main__":
    raise SystemExit(main())
