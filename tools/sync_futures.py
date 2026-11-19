"""Run one read-only public dollar-futures synchronization."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from market_data.providers.a3_public_futures import A3PublicFuturesProvider  # noqa: E402
from market_data.services.futures_sync import FuturesSyncService  # noqa: E402
from market_data.storage.futures_repository import SqliteFuturesRepository  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update observed public DLR contracts and recent trades once."
    )
    parser.add_argument(
        "--database",
        default="data/market/market_data.sqlite",
        help="Shared local SQLite database path.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if sys.version_info < (3, 9):
        print("ERROR: Fixed Income Toolkit requires Python 3.9 or newer.")
        return 2
    database_path = Path(args.database)
    if not database_path.is_absolute():
        database_path = _REPO_ROOT / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with SqliteFuturesRepository(str(database_path)) as repository:
        repository.initialize()
        service = FuturesSyncService(A3PublicFuturesProvider(), repository)
        contracts = service.refresh_contracts()
        trades = service.refresh_trades()

    print(
        "DLR actualizados | contratos: {} | operaciones recibidas: {} | "
        "operaciones nuevas: {} | contratos con error: {}".format(
            contracts.contracts_saved,
            trades.trades_received,
            trades.trades_saved,
            len(trades.contracts_failed),
        )
    )
    if trades.contracts_failed:
        print("Sin respuesta reciente: {}".format(", ".join(trades.contracts_failed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
