"""Read-only provider for public Secretaría de Finanzas auction results."""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Callable, Dict, Tuple

from market_data.models.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
)
from market_data.models.instrument_lifecycle import (
    TreasuryInstrumentCandidate,
    TreasuryResultNotice,
)
from market_data.providers.treasury.normalization import (
    parse_result_candidates,
    parse_result_notices,
)

Transport = Callable[[str, Dict[str, str], int], str]

_DEFAULT_LISTING_URL = "https://www.argentina.gob.ar/economia/finanzas/noticias"


def _default_transport(url: str, headers: Dict[str, str], timeout: int) -> str:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    except urllib.error.HTTPError as exc:
        raise ProviderResponseError(
            "Secretaría de Finanzas returned HTTP {}.".format(exc.code)
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        # A read timeout mid-response raises a bare TimeoutError (socket.timeout
        # in <=3.9), which is not a URLError, so it must be caught explicitly and
        # translated to a domain error the scheduler can skip without crashing.
        raise ProviderConnectionError(
            "Timed out reaching Secretaría de Finanzas after {}s.".format(timeout)
        ) from exc
    except urllib.error.URLError as exc:
        raise ProviderConnectionError(
            "Cannot reach Secretaría de Finanzas: {}".format(exc.reason)
        ) from exc


class TreasuryAuctionProvider:
    """Discover and normalize public result pages; never calculates values."""

    def __init__(
        self,
        listing_url: str = _DEFAULT_LISTING_URL,
        timeout_seconds: int = 15,
        transport: Transport = _default_transport,
    ) -> None:
        self._listing_url = listing_url
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._headers = {
            "accept": "text/html,application/xhtml+xml",
            "user-agent": "Fixed-Income-Toolkit/0.1 (+source acquisition)",
        }

    def list_result_notices(self) -> Tuple[TreasuryResultNotice, ...]:
        """List result articles currently exposed by the official news page."""
        body = self._transport(
            self._listing_url, self._headers, self._timeout_seconds
        )
        return parse_result_notices(body, self._listing_url)

    def fetch_candidates(
        self, notice: TreasuryResultNotice
    ) -> Tuple[TreasuryInstrumentCandidate, ...]:
        """Fetch one result article and return its national-Treasury rows."""
        body = self._transport(notice.url, self._headers, self._timeout_seconds)
        return parse_result_candidates(
            body,
            source_url=notice.url,
            retrieved_at=datetime.now(timezone.utc),
        )
