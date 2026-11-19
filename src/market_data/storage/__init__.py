"""Persistence for the Market Data layer.

Defines the :class:`MarketDataRepository` Protocol and its SQLite implementation.
Parquet export is added in a later stage.
"""

from __future__ import annotations

from market_data.storage.base import MarketDataRepository
from market_data.storage.lifecycle_repository import (
    InstrumentLifecycleRepository,
    SqliteLifecycleRepository,
)
from market_data.storage.sqlite_repository import SqliteRepository
from market_data.storage.futures_repository import SqliteFuturesRepository

__all__ = [
    "InstrumentLifecycleRepository",
    "MarketDataRepository",
    "SqliteLifecycleRepository",
    "SqliteRepository",
    "SqliteFuturesRepository",
]
