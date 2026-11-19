"""Decoupled configuration for the Market Data layer.

Nothing is hard-coded in business logic. Credentials are never stored here: the
API key is read from the environment on demand, so it can live only in a local,
git-ignored ``.env`` (see ``.env.example``). Loading a ``.env`` file into the
environment is the caller's responsibility (e.g. ``python-dotenv`` or the shell).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Tuple

from market_data.models.enums import (
    ApiEnvironment,
    InstrumentClass,
    Market,
    ProviderName,
)
from market_data.models.exceptions import ConfigurationError

# Official hosts (from the A3 / MAE MarketData documentation).
_HOST_BY_ENV = {
    ApiEnvironment.PROD: "https://api.mae.com.ar",
    ApiEnvironment.UAT: "https://apiuat.mae.com.ar",
}


@dataclass(frozen=True)
class A3ApiConfig:
    """Connection settings for the A3 / MAE MarketData API.

    Attributes:
        environment: UAT (test) or PROD (production).
        base_path: Path prefix after the host. The official curl uses
            ``MarketData/v1``; the Swagger paths use ``api/v1``. Confirm against
            a UAT call and adjust here if needed — no other code changes.
        api_key_env_uat: Environment variable holding the UAT API key.
        api_key_env_prod: Environment variable holding the production API key.
        timeout_seconds: HTTP request timeout.
    """

    environment: ApiEnvironment = ApiEnvironment.UAT
    base_path: str = "MarketData/v1"
    api_key_env_uat: str = "A3_MARKETDATA_API_KEY_UAT"
    api_key_env_prod: str = "A3_MARKETDATA_API_KEY_PROD"
    env_selector_var: str = "A3_MARKETDATA_ENV"
    timeout_seconds: int = 15

    @classmethod
    def from_env(cls, **overrides: object) -> "A3ApiConfig":
        """Build a config choosing the environment from ``A3_MARKETDATA_ENV``.

        Reads the ``A3_MARKETDATA_ENV`` variable (``UAT`` by default; ``PROD``
        selects production). The API key itself is never read here — only which
        environment to target. Any keyword overrides are passed through.
        """
        raw = os.environ.get("A3_MARKETDATA_ENV", "UAT").strip().upper()
        environment = (
            ApiEnvironment.PROD if raw == "PROD" else ApiEnvironment.UAT
        )
        return cls(environment=environment, **overrides)  # type: ignore[arg-type]

    def base_url(self) -> str:
        """Return the base URL for the configured environment."""
        host = _HOST_BY_ENV[self.environment]
        return "{host}/{path}".format(host=host, path=self.base_path.strip("/"))

    def api_key(self) -> str:
        """Read the API key for the configured environment from the environment.

        Returns:
            The API key string.

        Raises:
            ConfigurationError: If the corresponding environment variable is
                unset or empty. The key is never stored in code or config files.
        """
        var = (
            self.api_key_env_prod
            if self.environment is ApiEnvironment.PROD
            else self.api_key_env_uat
        )
        key = os.environ.get(var, "").strip()
        if not key:
            raise ConfigurationError(
                "Missing A3 MarketData API key: environment variable "
                "'{var}' is not set. Put it in a local .env (git-ignored) "
                "and load it into the environment.".format(var=var)
            )
        return key


@dataclass(frozen=True)
class ProviderConfig:
    """Which provider to use and what to request from it."""

    provider: ProviderName = ProviderName.A3
    market: Market = Market.A3
    instrument_classes: Tuple[InstrumentClass, ...] = (InstrumentClass.FIXED_INCOME,)
    a3_api: A3ApiConfig = field(default_factory=A3ApiConfig)


@dataclass(frozen=True)
class CacheConfig:
    """Cache behavior to avoid redundant provider calls."""

    enabled: bool = True
    ttl_seconds: int = 300


@dataclass(frozen=True)
class StorageConfig:
    """Where persisted data and exports live."""

    database_path: str = "data/market/market_data.sqlite"
    export_directory: str = "data/market/exports"


@dataclass(frozen=True)
class A3PublicFuturesConfig:
    """Connection policy for A3's provisional public futures viewer."""

    base_url: str = "https://matbarofex.primary.ventures/api/v2"
    timeout_seconds: int = 20
    contract_update_frequency_seconds: int = 86400
    trade_update_frequency_seconds: int = 900


@dataclass(frozen=True)
class MarketDataSettings:
    """Top-level configuration for the Market Data layer."""

    provider: ProviderConfig = field(default_factory=ProviderConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    # Backward-compatible name: this is the A3 market-data interval.
    update_frequency_seconds: int = 900
    treasury_update_frequency_seconds: int = 86400

    @property
    def a3_update_frequency_seconds(self) -> int:
        """Return the approved A3 refresh interval (15 minutes)."""
        return self.update_frequency_seconds
