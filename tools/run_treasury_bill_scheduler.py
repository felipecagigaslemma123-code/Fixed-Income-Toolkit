"""Run the approved Treasury/A3 lifecycle schedule in the foreground.

Secretaría de Finanzas is refreshed every 24 hours. A3 fixed income is refreshed
every 15 minutes. Both jobs run immediately when this process starts. No
financial calculation is executed.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from market_data.config.settings import (  # noqa: E402
    A3ApiConfig,
    MarketDataSettings,
    StorageConfig,
)
from market_data.models.enums import ApiEnvironment  # noqa: E402
from market_data.providers.a3mae.provider import A3MaeProvider  # noqa: E402
from market_data.providers.treasury.provider import TreasuryAuctionProvider  # noqa: E402
from market_data.services.lifecycle_scheduler import (  # noqa: E402
    SchedulerTickResult,
    TreasuryBillLifecycleScheduler,
)
from market_data.services.treasury_bill_sync import TreasuryBillSyncService  # noqa: E402
from market_data.storage.lifecycle_repository import SqliteLifecycleRepository  # noqa: E402
from market_data.storage.sqlite_repository import SqliteRepository  # noqa: E402


def _load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("\"").strip("'")
        if name:
            os.environ.setdefault(name, value)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run daily Treasury and 15-minute A3 lifecycle refreshes."
    )
    parser.add_argument(
        "--environment", choices=("UAT", "PROD"), default="UAT"
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required safety acknowledgement for production.",
    )
    parser.add_argument(
        "--max-result-articles",
        type=int,
        default=None,
        help="Optional cap applied to each daily Treasury refresh.",
    )
    parser.add_argument(
        "--database",
        default=StorageConfig().database_path,
        help="SQLite lifecycle database path.",
    )
    parser.add_argument(
        "--lock-file",
        default="data/market/treasury_a3_scheduler.lock",
        help="Process lock preventing duplicate local schedulers.",
    )
    return parser.parse_args()


def _print_tick(now: datetime, tick: SchedulerTickResult) -> None:
    timestamp = now.isoformat()
    if tick.treasury is not None:
        print(
            timestamp,
            "| Treasury OK | articles:",
            tick.treasury.notices_checked,
            "| candidates:",
            tick.treasury.candidates_discovered,
            flush=True,
        )
    elif tick.treasury_error is not None:
        print(timestamp, "| Treasury ERROR |", tick.treasury_error, flush=True)

    if tick.a3 is not None:
        print(
            timestamp,
            "| A3 OK | quotes:",
            tick.a3.quotes_received,
            "| saved:",
            tick.a3.quotes_saved,
            "| active:",
            tick.a3.active_for_analysis,
            "| pending:",
            tick.a3.pending_secondary_market + tick.a3.pending_match,
            flush=True,
        )
    elif tick.a3_error is not None:
        print(timestamp, "| A3 ERROR |", tick.a3_error, flush=True)


def main() -> int:
    args = _arguments()
    if args.environment == "PROD" and not args.allow_production:
        print("ERROR: production requires the explicit --allow-production flag")
        return 2
    if args.max_result_articles is not None and args.max_result_articles < 1:
        print("ERROR: --max-result-articles must be at least 1")
        return 2

    _load_local_env(_REPO_ROOT / ".env")
    environment = (
        ApiEnvironment.PROD if args.environment == "PROD" else ApiEnvironment.UAT
    )
    database_path = Path(args.database)
    if not database_path.is_absolute():
        database_path = _REPO_ROOT / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = Path(args.lock_file)
    if not lock_path.is_absolute():
        lock_path = _REPO_ROOT / lock_path
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = lock_path.open("a+")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_handle.close()
        print("Lifecycle scheduler already running; duplicate start skipped.")
        return 0

    settings = MarketDataSettings()
    repository = SqliteLifecycleRepository(str(database_path))
    repository.initialize()
    quote_repository = SqliteRepository(str(database_path))
    quote_repository.initialize()
    sync_service = TreasuryBillSyncService(
        TreasuryAuctionProvider(),
        A3MaeProvider(A3ApiConfig(environment=environment)),
        repository,
        quote_repository=quote_repository,
    )
    scheduler = TreasuryBillLifecycleScheduler(
        sync_service,
        treasury_interval_seconds=settings.treasury_update_frequency_seconds,
        a3_interval_seconds=settings.a3_update_frequency_seconds,
        max_result_articles=args.max_result_articles,
    )

    print(
        "Lifecycle scheduler started | environment:",
        environment.value,
        "| Treasury: 24h | A3: 15m",
        flush=True,
    )
    try:
        while True:
            now = datetime.now(timezone.utc)
            _print_tick(now, scheduler.run_due(now))
            wait_seconds = scheduler.seconds_until_next(datetime.now(timezone.utc))
            time.sleep(min(max(wait_seconds, 1), 60))
    except KeyboardInterrupt:
        print("Lifecycle scheduler stopped.", flush=True)
        return 0
    finally:
        repository.close()
        quote_repository.close()
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
