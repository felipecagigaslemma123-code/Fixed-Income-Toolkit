"""Read-only provider for A3's provisional public futures viewer."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable, Dict, Tuple

from market_data.config.settings import A3PublicFuturesConfig
from market_data.models.enums import ProviderName
from market_data.models.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
)
from market_data.models.futures import (
    FuturesContractReference,
    FuturesTradeObservation,
)
from market_data.providers.a3_public_futures.normalization import (
    parse_contracts,
    parse_trades,
)

Transport = Callable[[str, Dict[str, str], int], str]


def _default_transport(url: str, headers: Dict[str, str], timeout: int) -> str:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    except urllib.error.HTTPError as exc:
        raise ProviderResponseError(
            "A3 public futures viewer returned HTTP {}.".format(exc.code)
        ) from exc
    except urllib.error.URLError as exc:
        raise ProviderConnectionError(
            "Cannot reach A3 public futures viewer: {}".format(exc.reason)
        ) from exc


class A3PublicFuturesProvider:
    """Fetch DLR references and recent trades without credentials or formulas."""

    name = ProviderName.A3_PUBLIC_VIEWER

    def __init__(
        self,
        config: A3PublicFuturesConfig = A3PublicFuturesConfig(),
        transport: Transport = _default_transport,
    ) -> None:
        self._config = config
        self._transport = transport

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": "Fixed-Income-Toolkit/0.1 (local read-only prototype)",
        }

    def fetch_contracts(self) -> Tuple[FuturesContractReference, ...]:
        retrieved_at = datetime.now(timezone.utc)
        body = self._transport(
            "{}/ref-data".format(self._config.base_url.rstrip("/")),
            self._headers,
            self._config.timeout_seconds,
        )
        return parse_contracts(body, retrieved_at)

    def fetch_recent_trades(
        self, contract: FuturesContractReference
    ) -> Tuple[FuturesTradeObservation, ...]:
        received_at = datetime.now(timezone.utc)
        security_id = urllib.parse.quote(contract.security_id, safe="")
        url = "{}/trades/securities/{}".format(
            self._config.base_url.rstrip("/"), security_id
        )
        body = self._transport(
            url,
            self._headers,
            self._config.timeout_seconds,
        )
        return parse_trades(body, contract, received_at)

    def health_check(self) -> bool:
        try:
            return bool(self.fetch_contracts())
        except Exception:
            return False
