"""Loopback-only HTTP server for the approved local HTML dashboard."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type
from urllib.parse import parse_qsl, urlsplit

from local_dashboard.data import futures_payload, lifecycle_payload, market_quotes_payload
from local_dashboard.metrics import MetricsRequestError, metrics_payload


class LocalDashboardServer(ThreadingHTTPServer):
    """HTTP server carrying only the fixed dashboard and database paths."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: Type[BaseHTTPRequestHandler],
        dashboard_path: Path,
        database_path: Path,
        futures_dashboard_path: Optional[Path] = None,
    ) -> None:
        self.dashboard_path = dashboard_path
        self.futures_dashboard_path = futures_dashboard_path
        self.database_path = database_path
        super().__init__(server_address, handler_class)


class LocalDashboardHandler(BaseHTTPRequestHandler):
    """Serve a small allowlist of read-only local resources."""

    server: LocalDashboardServer

    def _send_bytes(
        self,
        body: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
        cache_control: str = "no-store",
    ) -> None:
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(
        self,
        payload: Dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status)

    def _dashboard(self) -> None:
        try:
            body = self.server.dashboard_path.read_bytes()
        except OSError:
            self._send_json(
                {"status": "error", "message": "dashboard unavailable"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._send_bytes(body, "text/html; charset=utf-8")

    def _futures_dashboard(self) -> None:
        path = self.server.futures_dashboard_path
        if path is None:
            self._send_json(
                {"status": "error", "message": "futures dashboard unavailable"},
                HTTPStatus.NOT_FOUND,
            )
            return
        try:
            body = path.read_bytes()
        except OSError:
            self._send_json(
                {"status": "error", "message": "futures dashboard unavailable"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._send_bytes(body, "text/html; charset=utf-8")

    def _database_view(self, loader: Callable[[str], Dict[str, Any]]) -> None:
        try:
            payload = loader(str(self.server.database_path))
        except Exception:  # Boundary: never expose local paths or database details.
            self._send_json(
                {"status": "error", "message": "local database unavailable"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._send_json(payload)

    def _metrics(self, query: str) -> None:
        """Serve engine-computed metrics for one instrument evaluation.

        Read-only: the request carries contractual data, the selected price and
        the selected dates, and nothing is written. The dashboard HTML holds no
        financial formula; this is the single calculation path.
        """
        params = dict(parse_qsl(query, keep_blank_values=True))
        try:
            payload = metrics_payload(params)
        except MetricsRequestError as exc:
            self._send_json(
                {"status": "error", "message": str(exc)},
                HTTPStatus.BAD_REQUEST,
            )
            return
        except Exception:  # Boundary: never expose internals to the browser.
            self._send_json(
                {"status": "error", "message": "metrics unavailable"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._send_json(payload)

    def _health(self) -> None:
        try:
            quotes = market_quotes_payload(str(self.server.database_path))
            lifecycle = lifecycle_payload(str(self.server.database_path))
            futures = futures_payload(str(self.server.database_path))
        except Exception:
            self._send_json(
                {"status": "error", "database": "unavailable"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._send_json(
            {
                "status": "ok",
                "database": "available",
                "quote_count": len(quotes["quotes"]),
                "lifecycle_count": len(lifecycle["instruments"]),
                "futures_contract_count": len(futures["contracts"]),
                "futures_trade_count": futures["trade_count"],
            }
        )

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parts = urlsplit(self.path)
        path = parts.path
        if path in ("/", "/index.html"):
            self._dashboard()
        elif path in ("/futures", "/futures.html"):
            self._futures_dashboard()
        elif path == "/api/market/quotes":
            self._database_view(market_quotes_payload)
        elif path == "/api/lifecycle":
            self._database_view(lifecycle_payload)
        elif path == "/api/futures":
            self._database_view(futures_payload)
        elif path == "/api/metrics":
            self._metrics(parts.query)
        elif path == "/api/health":
            self._health()
        elif path == "/favicon.ico":
            self._send_bytes(b"", "image/x-icon", HTTPStatus.NO_CONTENT)
        else:
            self._send_json(
                {"status": "error", "message": "not found"},
                HTTPStatus.NOT_FOUND,
            )

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler API
        self.do_GET()

    def log_message(self, format: str, *args: object) -> None:
        """Keep normal local requests quiet; the CLI owns startup messages."""


def create_server(
    dashboard_path: Path,
    database_path: Path,
    port: int = 8765,
    futures_dashboard_path: Optional[Path] = None,
) -> LocalDashboardServer:
    """Create a server bound exclusively to the local loopback interface."""
    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return LocalDashboardServer(
        ("127.0.0.1", port),
        LocalDashboardHandler,
        dashboard_path=dashboard_path,
        database_path=database_path,
        futures_dashboard_path=futures_dashboard_path,
    )
