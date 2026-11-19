"""A3 / MAE MarketData provider.

Wraps the official A3 / MAE MarketData REST API (fixed income, cauciones, forex,
repo) behind the :class:`market_data.providers.base.MarketDataProvider` Protocol.
Network logic lives only in :mod:`provider`; the raw-to-domain mapping lives in
:mod:`normalization` and is pure and testable offline.

Contract: ``docs/providers/a3_provider_contract.md``.
"""

from __future__ import annotations

from market_data.providers.a3mae.normalization import parse_quotes
from market_data.providers.a3mae.provider import A3MaeProvider

__all__ = ["A3MaeProvider", "parse_quotes"]
