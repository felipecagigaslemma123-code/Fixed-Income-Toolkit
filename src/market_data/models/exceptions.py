"""Domain exception hierarchy for the Market Data layer.

Follows the project Exception Policy: one base exception plus specific domain
exceptions. Generic exceptions are not exposed when a domain exception exists.
"""

from __future__ import annotations


class MarketDataError(Exception):
    """Base class for all Market Data domain errors."""


# --- Provider errors -------------------------------------------------------
class ProviderError(MarketDataError):
    """Base class for errors originating in a data provider."""


class ProviderConnectionError(ProviderError):
    """Raised when the provider cannot be reached."""


class ProviderResponseError(ProviderError):
    """Raised when the provider returns an unexpected or malformed response."""


class ProviderAuthError(ProviderError):
    """Raised when authentication with the provider fails."""


# --- Normalization ---------------------------------------------------------
class NormalizationError(MarketDataError):
    """Raised when a raw provider payload cannot be mapped to domain models."""


# --- Storage errors --------------------------------------------------------
class StorageError(MarketDataError):
    """Base class for persistence errors."""


class SchemaVersionError(StorageError):
    """Raised when the on-disk schema version is incompatible."""


class RepositoryIntegrityError(StorageError):
    """Raised when a persistence invariant is violated."""


# --- Configuration and cache ----------------------------------------------
class ConfigurationError(MarketDataError):
    """Raised when configuration is missing or invalid."""


class CacheError(MarketDataError):
    """Raised when the cache layer fails in a non-recoverable way."""
