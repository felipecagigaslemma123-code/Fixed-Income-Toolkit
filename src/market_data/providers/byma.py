"""Read-only access to the documented BYMA Market Data gateway."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from market_data.models.exceptions import (
    ConfigurationError,
    ProviderAuthError,
    ProviderConnectionError,
    ProviderResponseError,
)

_GATEWAY = "https://apigw.byma.com.ar"
_FIXED_INCOME = (
    ("group", "LETRASTESORO"),
    ("market", "PPT"),
    ("operativeform", "CONTADO"),
    ("currency", "ARS"),
    ("settlperiod", "0002"),
)
_DATE_RANGES = (("from", "to"), ("fromdate", "todate"), ("fromStartDate", "toStartDate"))
_DATE_PARAMS = {"date"} | {name for bounds in _DATE_RANGES for name in bounds}


@dataclass(frozen=True)
class _Operation:
    path: str
    scope: str
    parameters: tuple[tuple[str, Optional[str]], ...] = ()
    required: tuple[str, ...] = ()
    csv: bool = False


_OPERATIONS = {
    "eod": _Operation(
        "/eod/v1/fixed_income.raw/", "BYMA_EOD_SCOPE", _FIXED_INCOME + (("page", "0"),)
    ),
    "delay20": _Operation("/delay20/v1/fixed_income", "BYMA_DELAY20_SCOPE", _FIXED_INCOME),
    "placements": _Operation(
        "/byma-primarias-placements/v1/historical-placements.json/",
        "bymaPrimariasPlacements.read",
        (
            ("page", "0"), ("size", "10"), ("fromStartDate", None), ("toStartDate", None),
            ("issuerId", None), ("underwriterId", None), ("placementId", None),
        ),
    ),
    "indices": _Operation(
        "/byma-indices/v1/caucion/eod.csv/", "indicesByma.eod.read",
        (("fromdate", None), ("todate", None), ("page", "0")), ("fromdate", "todate"),
        csv=True,
    ),
    "indices-intraday": _Operation(
        "/byma-indices/v1/caucion/intraday.csv/", "indicesByma.intraday.read", (("page", "0"),),
        csv=True,
    ),
    "dollar-eod": _Operation(
        "/indice-dolar-byma/v1/eod.json/", "indiceDolarBYMA.eod.read", (("date", None),)
    ),
    "dollar-intraday": _Operation(
        "/indice-dolar-byma/v1/intraday.json/", "indiceDolarBYMA.intraday.read"
    ),
    "instruments": _Operation(
        "/market-data-instruments/v1/fixedincome.json/", "marketDataInstruments.read",
        (("group", "LETRASTESORO"), ("market", "PPT")),
    ),
    "news": _Operation(
        "/market-data-news/v1/relevant-events.json/", "marketDataNews.read", (("date", None),)
    ),
    "economic-indicators": _Operation(
        "/economic-indicators/v1/principales-variables/variables.json/", "economicIndicators.read"
    ),
    "economic-series": _Operation(
        "/economic-indicators/v1/principales-variables/variables/{id}.json/",
        "economicIndicators.read",
        (("id", None), ("from", None), ("to", None)), ("id", "from", "to"),
    ),
}
BYMA_OPERATIONS = tuple(_OPERATIONS)


@dataclass(frozen=True)
class BymaResponse:
    """Original payload and the local time at which the gateway returned it."""

    body: bytes
    received_at: datetime
    format: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Credentials and tokens are only sent to the configured gateway.


def _send(request: Request, timeout: int) -> bytes:
    label = "token OAuth" if request.get_method() == "POST" else "consulta de datos"
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        if exc.code in (401, 403) or (exc.code == 400 and request.get_method() == "POST"):
            raise ProviderAuthError(f"BYMA rechazó {label} (HTTP {exc.code}).") from None
        raise ProviderResponseError(f"BYMA devolvió HTTP {exc.code} en {label}.") from None
    except (URLError, OSError):
        raise ProviderConnectionError(f"No se pudo conectar con BYMA para {label}.") from None


def _read_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Falta configurar {name} en el entorno local.")
    return value


def _decode_json(body: bytes):
    try:
        return json.loads(body)
    except ValueError:
        raise ProviderResponseError("BYMA devolvió un cuerpo que no es JSON válido.") from None


def _query_parameters(operation: _Operation, overrides: Mapping[str, str]) -> dict[str, str]:
    defaults = dict(operation.parameters)
    unknown = overrides.keys() - defaults.keys()
    if unknown:
        raise ConfigurationError(f"Parámetros BYMA no admitidos: {', '.join(sorted(unknown))}.")
    parameters = {key: value for key, value in {**defaults, **overrides}.items() if value is not None}
    for key, value in parameters.items():
        if not value or value != value.strip():
            raise ConfigurationError(f"El parámetro BYMA {key} requiere un valor sin espacios exteriores.")
        if key in _DATE_PARAMS:
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError:
                raise ConfigurationError(f"El parámetro BYMA {key} requiere una fecha AAAA-MM-DD.") from None
        if key in {"page", "size", "id"}:
            if not re.fullmatch(r"[0-9]+", value) or (key != "page" and not value.lstrip("0")):
                raise ConfigurationError(f"El parámetro BYMA {key} tiene un entero fuera de rango.")
    missing = set(operation.required) - parameters.keys()
    if missing:
        raise ConfigurationError(f"Faltan parámetros BYMA: {', '.join(sorted(missing))}.")
    for start, end in _DATE_RANGES:
        if start in parameters and end in parameters and parameters[start] > parameters[end]:
            raise ConfigurationError(f"El parámetro BYMA {start} debe preceder o igualar a {end}.")
    return parameters


class BymaMarketDataClient:
    """Query a BYMA operation with a token limited to its documented permission."""

    def __init__(self, transport: Callable[[Request, int], bytes] = _send):
        self._transport = transport

    def _token(self, scope: str) -> str:
        body = urlencode({
            "grant_type": "client_credentials",
            "client_id": _read_env("BYMA_CLIENT_ID"),
            "client_secret": _read_env("BYMA_CLIENT_SECRET"),
            "scope": scope,
        }).encode("ascii")
        request = Request(
            f"{_GATEWAY}/oauth/token/", data=body, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        payload = _decode_json(self._transport(request, 20))
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token):
            raise ProviderAuthError("BYMA no devolvió un token Bearer válido.")
        return token

    def fetch(self, name: str, parameters: Optional[Mapping[str, str]] = None) -> BymaResponse:
        """Fetch a single response, preserving the original data and pagination metadata."""
        try:
            operation = _OPERATIONS[name]
        except KeyError:
            raise ConfigurationError("Operación BYMA desconocida.") from None
        query = _query_parameters(operation, parameters or {})
        path = operation.path
        if name == "economic-series":
            path = path.format(id=query.pop("id"))
        url = f"{_GATEWAY}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        scope = operation.scope
        if scope.startswith("BYMA_"):
            scope = _read_env(scope)
        token = self._token(scope)
        request = Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "text/csv" if operation.csv else "application/json",
        })
        body = self._transport(request, 20)
        received_at = datetime.now(timezone.utc)
        if operation.csv:
            data = body.removeprefix(b"\xef\xbb\xbf").lstrip()
            if not data or data.startswith((b"<", b"{", b"[")):
                raise ProviderResponseError("BYMA no devolvió el CSV solicitado.")
            return BymaResponse(body, received_at, "CSV")

        payload = _decode_json(body)
        if not isinstance(payload, (dict, list)):
            raise ProviderResponseError("BYMA devolvió un JSON con una estructura inesperada.")
        if isinstance(payload, dict) and (payload.get("error") or payload.get("type") == "OOS"):
            raise ProviderResponseError("BYMA informó un error en la consulta de datos.")
        if name in ("eod", "delay20") and (
            not isinstance(payload, dict) or not isinstance(payload.get("result"), list)
        ):
            raise ProviderResponseError("BYMA no devolvió la lista esperada de cotizaciones.")
        return BymaResponse(body, received_at, "JSON")
