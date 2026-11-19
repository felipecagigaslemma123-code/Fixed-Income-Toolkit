"""Manual smoke test for the A3 / MAE MarketData provider (UAT).

Run this locally with your UAT API key in the environment. It performs a REAL
network call to the A3 UAT endpoint and prints a few fixed-income quotes. It is
NOT part of the automated test suite (which is fully offline).

Usage:
    1. Copy .env.example to .env and put your UAT key in A3_MARKETDATA_API_KEY_UAT.
    2. Load it into the environment, e.g.:
         set -a && source .env && set +a
    3. Run:
         python tools/smoke_a3mae_uat.py

Nothing here stores or prints your API key.
"""

from __future__ import annotations

import os
import sys

# Allow running from the repo root without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from market_data.config.settings import A3ApiConfig  # noqa: E402
from market_data.models.enums import ApiEnvironment, InstrumentClass  # noqa: E402
from market_data.models.exceptions import MarketDataError  # noqa: E402
from market_data.providers.a3mae.provider import A3MaeProvider  # noqa: E402
from market_data.providers.base import QuoteQuery  # noqa: E402


def main() -> int:
    config = A3ApiConfig(environment=ApiEnvironment.UAT)
    provider = A3MaeProvider(config)
    print("Base URL:", config.base_url())
    try:
        quotes = provider.fetch_quotes(
            QuoteQuery(instrument_class=InstrumentClass.FIXED_INCOME)
        )
    except MarketDataError as exc:
        print("ERROR:", type(exc).__name__, "-", exc)
        return 1

    print("Fixed-income quotes received:", len(quotes))
    for q in quotes[:5]:
        print(
            " -",
            q.ticker,
            "| last:",
            q.last_price,
            "| close:",
            q.close_price,
            "| rate:",
            q.provider_rate,
            "| date:",
            q.market_date,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
