"""A3 / MAE MarketData provider implementation.

Uses only the Python standard library (``urllib``) to avoid an extra dependency.
The API key is read from the environment via :class:`A3ApiConfig`; it is never
stored in code. The HTTP transport is injectable so the provider can be tested
fully offline with fixtures.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, Dict, Tuple

from market_data.config.settings import A3ApiConfig
from market_data.models.enums import InstrumentClass, ProviderName
from market_data.models.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderResponseError,
)
from market_data.models.quote import MarketQuote
from market_data.providers.a3mae.normalization import parse_quotes
from market_data.providers.base import QuoteQuery

# A transport takes (url, headers, timeout) and returns the response body text,
# or raises a ProviderError subclass. Injectable for testing.
Transport = Callable[[str, Dict[str, str], int], str]

# Segment -> endpoint path (relative to the configured base URL).
_ENDPOINT_BY_CLASS = {
    InstrumentClass.FIXED_INCOME: "mercado/cotizaciones/rentafija",
    InstrumentClass.CAUCION: "mercado/cotizaciones/cauciones",
    InstrumentClass.FOREX: "mercado/cotizaciones/forex",
    InstrumentClass.REPO: "mercado/repo",
}

_PAGE_SIZE = 50
_MAX_PAGES = 100


def _default_transport(url: str, headers: Dict[str, str], timeout: int) -> str:
    """Perform a GET request with urllib and return the body text.

    Raises:
        ProviderAuthError: On HTTP 401/403.
        ProviderResponseError: On other HTTP error status codes.
        ProviderConnectionError: On connection/timeout failures.
    """
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ProviderAuthError(
                "A3 MarketData authentication failed (HTTP {}).".format(exc.code)
            ) from exc
        raise ProviderResponseError(
            "A3 MarketData returned HTTP {}.".format(exc.code)
        ) from exc
    except urllib.error.URLError as exc:
        raise ProviderConnectionError(
            "Cannot reach A3 MarketData: {}".format(exc.reason)
        ) from exc


class A3MaeProvider:
    """Market data provider backed by the A3 / MAE MarketData REST API."""

    name = ProviderName.A3

    def __init__(self, config: A3ApiConfig, transport: Transport = _default_transport):
        """Initialize the provider.

        Args:
            config: Connection configuration (environment, base path, key source).
            transport: HTTP transport callable; defaults to the urllib transport.
                Inject a fake transport in tests to run offline.
        """
        self._config = config
        self._transport = transport

    def _build_url(self, query: QuoteQuery) -> str:
        """Build the request URL for a query, including filter parameters."""
        try:
            endpoint = _ENDPOINT_BY_CLASS[query.instrument_class]
        except KeyError as exc:
            raise ProviderError(
                "A3 MarketData does not serve instrument class {}.".format(
                    query.instrument_class.value
                )
            ) from exc
        params = {
            "segmento": query.segmento,
            "plazo": query.plazo,
            "moneda": query.moneda,
            "ticker": query.ticker,
            "pageNumber": query.page_number,
        }
        clean = {k: v for k, v in params.items() if v is not None and v != ""}
        url = "{base}/{endpoint}".format(
            base=self._config.base_url(), endpoint=endpoint
        )
        if clean:
            url = "{url}?{qs}".format(url=url, qs=urllib.parse.urlencode(clean))
        return url

    def _fetch_page(
        self, query: QuoteQuery, retrieved_at: datetime
    ) -> Tuple[MarketQuote, ...]:
        """Fetch and normalize one explicit API page."""
        url = self._build_url(query)
        headers = {"x-api-key": self._config.api_key(), "accept": "application/json"}
        body = self._transport(url, headers, self._config.timeout_seconds)
        return parse_quotes(body, query.instrument_class, self.name, retrieved_at)

    def fetch_quotes(self, query: QuoteQuery) -> Tuple[MarketQuote, ...]:
        """Fetch and normalize quotes, exhausting A3 pagination by default.

        Args:
            query: Segment and optional filters.

        Returns:
            The normalized quotes. When ``page_number`` is omitted, all pages
            are fetched and duplicate boundary records are consolidated by the
            same natural identity used by SQLite. Supplying ``page_number``
            requests exactly that page.

        Raises:
            ProviderError: On connection, authentication or response errors.
            ConfigurationError: If the API key is not available in the environment.
            NormalizationError: If the response cannot be mapped.
        """
        retrieved_at = datetime.now(timezone.utc)
        if query.page_number is not None:
            return self._fetch_page(query, retrieved_at)

        quotes_by_identity = {}
        for page_number in range(1, _MAX_PAGES + 1):
            page = self._fetch_page(
                replace(query, page_number=page_number), retrieved_at
            )
            for quote in page:
                identity = (
                    quote.ticker,
                    quote.instrument_class,
                    quote.term,
                    quote.market_date,
                    quote.provider,
                )
                quotes_by_identity[identity] = quote
            if len(page) < _PAGE_SIZE:
                return tuple(quotes_by_identity.values())

        raise ProviderResponseError(
            "A3 MarketData pagination exceeded the {}-page safety limit.".format(
                _MAX_PAGES
            )
        )

    def health_check(self) -> bool:
        """Return ``True`` if a minimal fixed-income request succeeds."""
        try:
            self.fetch_quotes(
                QuoteQuery(instrument_class=InstrumentClass.FIXED_INCOME, page_number=1)
            )
            return True
        except Exception:  # availability probe: any failure means "not healthy"
            return False
