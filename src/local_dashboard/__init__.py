"""Local, read-only bridge between Toolkit SQLite data and the HTML dashboard."""

from __future__ import annotations

from local_dashboard.data import lifecycle_payload, market_quotes_payload
from local_dashboard.server import create_server

__all__ = ["create_server", "lifecycle_payload", "market_quotes_payload"]
