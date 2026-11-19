"""Synchronize official national-Treasury results with A3 visibility.

This command performs read-only requests to Secretaría de Finanzas and A3,
stores source evidence plus operational lifecycle state in SQLite, and executes
no financial calculation.

Examples:
    python tools/sync_treasury_bills.py
    python tools/sync_treasury_bills.py --max-result-articles 3
    python tools/sync_treasury_bills.py --environment PROD --allow-production
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from market_data.config.settings import A3ApiConfig, StorageConfig  # noqa: E402
from market_data.models.enums import ApiEnvironment  # noqa: E402
from market_data.models.exceptions import MarketDataError  # noqa: E402
from market_data.providers.a3mae.provider import A3MaeProvider  # noqa: E402
from market_data.providers.treasury.provider import TreasuryAuctionProvider  # noqa: E402
from market_data.services.treasury_bill_sync import TreasuryBillSyncService  # noqa: E402
from market_data.storage.lifecycle_repository import SqliteLifecycleRepository  # noqa: E402
from market_data.storage.sqlite_repository import SqliteRepository  # noqa: E402


def _load_local_env(path: Path) -> None:
    """Load a simple local .env without printing or overriding credentials."""
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
        description=(
            "Stage national-Treasury results and activate instruments observed by A3."
        )
    )
    parser.add_argument(
        "--environment",
        choices=("UAT", "PROD"),
        default="UAT",
        help="A3 environment (default: UAT).",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required safety acknowledgement when --environment PROD is used.",
    )
    parser.add_argument(
        "--max-result-articles",
        type=int,
        default=None,
        help="Optional limit for official result articles checked in this run.",
    )
    parser.add_argument(
        "--database",
        default=StorageConfig().database_path,
        help="SQLite lifecycle database path.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.max_result_articles is not None and args.max_result_articles < 1:
        print("ERROR: --max-result-articles must be at least 1")
        return 2
    if args.environment == "PROD" and not args.allow_production:
        print("ERROR: production requires the explicit --allow-production flag")
        return 2

    _load_local_env(_REPO_ROOT / ".env")
    environment = (
        ApiEnvironment.PROD if args.environment == "PROD" else ApiEnvironment.UAT
    )
    database_path = Path(args.database)
    if not database_path.is_absolute():
        database_path = _REPO_ROOT / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)

    repository = SqliteLifecycleRepository(str(database_path))
    repository.initialize()
    quote_repository = SqliteRepository(str(database_path))
    quote_repository.initialize()
    service = TreasuryBillSyncService(
        TreasuryAuctionProvider(),
        A3MaeProvider(A3ApiConfig(environment=environment)),
        repository,
        quote_repository=quote_repository,
    )
    try:
        result = service.run(max_result_articles=args.max_result_articles)
    except MarketDataError as exc:
        print("ERROR:", type(exc).__name__, "-", exc)
        return 1
    finally:
        repository.close()
        quote_repository.close()

    print("Environment:", environment.value)
    print("Official result articles checked:", result.notices_checked)
    print("A3 fixed-income quotes received:", result.quotes_received)
    print("A3 fixed-income quotes saved:", result.quotes_saved)
    print("National-Treasury candidates evaluated:", result.candidates_evaluated)
    print("Active for analysis:", result.active_for_analysis)
    print("Pending secondary market:", result.pending_secondary_market)
    print("Pending safe match:", result.pending_match)
    print("Matured:", result.matured)
    for decision in result.decisions:
        print(
            " -",
            decision.candidate.ticker or "ticker pending",
            "->",
            decision.matched_ticker or "not matched",
            "|",
            decision.status.value,
            "|",
            decision.match_method.value,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
