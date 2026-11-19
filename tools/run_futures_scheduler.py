"""Run the local public dollar-futures observer in the foreground."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from market_data.config import A3PublicFuturesConfig  # noqa: E402
from market_data.providers.a3_public_futures import A3PublicFuturesProvider  # noqa: E402
from market_data.services.futures_scheduler import (  # noqa: E402
    FuturesScheduler,
    FuturesSchedulerTickResult,
)
from market_data.services.futures_sync import FuturesSyncService  # noqa: E402
from market_data.storage.futures_repository import SqliteFuturesRepository  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Observe public A3 dollar-futures data locally."
    )
    parser.add_argument(
        "--database",
        default="data/market/market_data.sqlite",
        help="Shared local SQLite database path.",
    )
    parser.add_argument("--contract-interval", type=int, default=86400)
    parser.add_argument("--trade-interval", type=int, default=900)
    return parser.parse_args()


def _print_tick(now: datetime, tick: FuturesSchedulerTickResult) -> None:
    timestamp = now.isoformat()
    if tick.contracts is not None:
        print(
            timestamp,
            "| DLR contracts:",
            tick.contracts.contracts_received,
            "| saved:",
            tick.contracts.contracts_saved,
            flush=True,
        )
    elif tick.contracts_error is not None:
        print(timestamp, "| DLR CONTRACT ERROR |", tick.contracts_error, flush=True)

    if tick.trades is not None:
        print(
            timestamp,
            "| DLR trades:",
            tick.trades.trades_received,
            "| new:",
            tick.trades.trades_saved,
            "| failed contracts:",
            len(tick.trades.contracts_failed),
            flush=True,
        )
    elif tick.trades_error is not None:
        print(timestamp, "| DLR TRADE ERROR |", tick.trades_error, flush=True)


def main() -> int:
    args = _arguments()
    if sys.version_info < (3, 9):
        print("ERROR: Fixed Income Toolkit requires Python 3.9 or newer.")
        return 2
    if args.contract_interval <= 0 or args.trade_interval <= 0:
        print("ERROR: update intervals must be positive")
        return 2

    database_path = Path(args.database)
    if not database_path.is_absolute():
        database_path = _REPO_ROOT / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)

    config = A3PublicFuturesConfig(
        contract_update_frequency_seconds=args.contract_interval,
        trade_update_frequency_seconds=args.trade_interval,
    )
    repository = SqliteFuturesRepository(str(database_path))
    repository.initialize()
    service = FuturesSyncService(A3PublicFuturesProvider(config), repository)
    scheduler = FuturesScheduler(
        service,
        contract_interval_seconds=config.contract_update_frequency_seconds,
        trade_interval_seconds=config.trade_update_frequency_seconds,
    )

    print(
        "Observador DLR iniciado | contratos: 24h | operaciones: 15m | "
        "fuente pública provisoria",
        flush=True,
    )
    try:
        while True:
            now = datetime.now(timezone.utc)
            _print_tick(now, scheduler.run_due(now))
            wait_seconds = scheduler.seconds_until_next(datetime.now(timezone.utc))
            time.sleep(min(max(wait_seconds, 1), 60))
    except KeyboardInterrupt:
        print("Observador DLR detenido.", flush=True)
        return 0
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
