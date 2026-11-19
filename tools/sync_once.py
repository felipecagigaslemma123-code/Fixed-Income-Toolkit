"""Run a single Treasury/A3 refresh and exit (for scheduled morning syncs).

Unlike ``run_treasury_bill_scheduler.py`` (a perpetual foreground loop meant to
run beside the dashboard), this performs exactly one pass and terminates, so it
can be driven by a macOS LaunchAgent on weekday mornings.

Priorities and failure policy:

* The A3 fixed-income refresh feeds the dashboard's current prices/yields and is
  the critical job. If it fails, the process exits non-zero.
* The Secretaría de Finanzas (Treasury) discovery refresh is best-effort. A
  network timeout or unreachable site is logged and skipped; it never fails the
  run, because A3 prices do not depend on it.

No financial calculation is executed here; this only acquires and stores
observations and lifecycle evidence.
"""

from __future__ import annotations

import argparse
import os
import sys
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
from market_data.models.exceptions import MarketDataError  # noqa: E402
from market_data.providers.a3mae.provider import A3MaeProvider  # noqa: E402
from market_data.providers.treasury.provider import TreasuryAuctionProvider  # noqa: E402
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
        value = value.strip().strip('"').strip("'")
        if name:
            os.environ.setdefault(name, value)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a single Treasury/A3 lifecycle refresh and exit."
    )
    parser.add_argument("--environment", choices=("UAT", "PROD"), default="UAT")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required safety acknowledgement for production.",
    )
    parser.add_argument(
        "--max-result-articles",
        type=int,
        default=None,
        help="Optional cap applied to the Treasury refresh.",
    )
    parser.add_argument(
        "--skip-treasury",
        action="store_true",
        help="Only refresh A3 prices; do not touch the Treasury source.",
    )
    parser.add_argument(
        "--database",
        default=StorageConfig().database_path,
        help="SQLite database path.",
    )
    return parser.parse_args()


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

    MarketDataSettings()  # validate configuration early
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

    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    print(stamp, "| sync_once start | environment:", environment.value, flush=True)

    a3_ok = False
    try:
        # Best-effort Treasury discovery: never let it fail the run.
        if not args.skip_treasury:
            try:
                treasury = sync_service.refresh_treasury(
                    evaluated_at=now,
                    max_result_articles=args.max_result_articles,
                )
                print(
                    stamp,
                    "| Treasury OK | articles:",
                    treasury.notices_checked,
                    "| candidates:",
                    treasury.candidates_discovered,
                    flush=True,
                )
            except MarketDataError as exc:
                print(
                    stamp,
                    "| Treasury SKIPPED |",
                    "{}: {}".format(type(exc).__name__, exc),
                    flush=True,
                )

        # Critical A3 refresh: drives dashboard prices/yields.
        try:
            a3 = sync_service.refresh_a3(evaluated_at=now)
            a3_ok = True
            print(
                stamp,
                "| A3 OK | quotes:",
                a3.quotes_received,
                "| saved:",
                a3.quotes_saved,
                "| active:",
                a3.active_for_analysis,
                flush=True,
            )
        except MarketDataError as exc:
            print(
                stamp,
                "| A3 ERROR |",
                "{}: {}".format(type(exc).__name__, exc),
                flush=True,
            )
    finally:
        repository.close()
        quote_repository.close()

    print(stamp, "| sync_once done | a3_ok:", a3_ok, flush=True)
    return 0 if a3_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
