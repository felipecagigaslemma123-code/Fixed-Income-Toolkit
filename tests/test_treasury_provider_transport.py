"""Network-failure translation for the Treasury HTTP transport.

The scheduler only skips a source gracefully when the provider raises a
``MarketDataError``. A read timeout mid-response surfaces as a bare
``TimeoutError`` (``socket.timeout`` on <=3.9), which is *not* a ``URLError``;
these tests pin that such low-level failures are translated into domain errors
so a single slow Treasury request can never crash the lifecycle scheduler.
"""
from __future__ import annotations

import socket
import unittest
from unittest import mock

from market_data.models.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
)
from market_data.providers.treasury.provider import _default_transport


class TreasuryTransportErrorTranslationTests(unittest.TestCase):
    def _assert_translates(self, raised: BaseException) -> None:
        with mock.patch(
            "market_data.providers.treasury.provider.urllib.request.urlopen",
            side_effect=raised,
        ):
            with self.assertRaises(ProviderConnectionError):
                _default_transport("https://example.test", {}, 15)

    def test_read_timeout_becomes_connection_error(self) -> None:
        self._assert_translates(TimeoutError("read timed out"))

    def test_socket_timeout_becomes_connection_error(self) -> None:
        self._assert_translates(socket.timeout("timed out"))

    def test_url_error_still_becomes_connection_error(self) -> None:
        import urllib.error

        self._assert_translates(urllib.error.URLError("no route"))

    def test_http_error_becomes_response_error(self) -> None:
        import urllib.error

        http_error = urllib.error.HTTPError(
            "https://example.test", 503, "Service Unavailable", {}, None
        )
        with mock.patch(
            "market_data.providers.treasury.provider.urllib.request.urlopen",
            side_effect=http_error,
        ):
            with self.assertRaises(ProviderResponseError):
                _default_transport("https://example.test", {}, 15)


if __name__ == "__main__":
    unittest.main()
