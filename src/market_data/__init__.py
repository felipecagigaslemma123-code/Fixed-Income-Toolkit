"""Market Data layer for the Fixed Income Toolkit.

This package is the single source of market data for the whole Toolkit. It
obtains, normalizes, stores and serves *raw* market data. It never invents
financial numbers: every rate/forward derivation is a financial calculation that
lives in the Financial Engine and is subject to the project Research Gate.

Stage 0 scope (this commit): domain models, enums, exception hierarchy,
configuration structures, and the provider/repository Protocols. No network, no
storage IO and no financial formulas are implemented here.

See ``docs/proposals/market_data_module_architecture.md`` (v1.2).
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.0.0"
