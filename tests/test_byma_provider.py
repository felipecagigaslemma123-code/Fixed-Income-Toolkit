"""Offline checks for BYMA paths, credential handling and raw responses."""

import os
import unittest
from datetime import timezone
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

from market_data.models.exceptions import (
    ConfigurationError,
    ProviderAuthError,
    ProviderResponseError,
)
from market_data.providers.byma import BymaMarketDataClient, _send


class BymaClientTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            "BYMA_CLIENT_ID": "demo-id",
            "BYMA_CLIENT_SECRET": "demo secret+&",
            "BYMA_EOD_SCOPE": "test.eod.read",
            "BYMA_DELAY20_SCOPE": "test.delay.read",
        })
        env.start()
        self.addCleanup(env.stop)
        self.requests = []
        self.token = b'{"access_token":"demo-token"}'
        self.body = b'{"result":[],"meta":{"nextPage":1}}'
        self.client = BymaMarketDataClient(self.transport)

    def transport(self, request, timeout):
        self.requests.append(request)
        return self.token if request.get_method() == "POST" else self.body

    def test_fixed_income_uses_distinct_routes_and_permissions(self):
        for name, path, scope in (
            ("eod", "/eod/v1/fixed_income.raw/", "test.eod.read"),
            ("delay20", "/delay20/v1/fixed_income", "test.delay.read"),
        ):
            with self.subTest(operation=name):
                response = self.client.fetch(name, {"group": "OBLIGACIONESNEGOC"})
                token_request, data_request = self.requests[-2:]
                self.assertEqual(token_request.full_url, "https://apigw.byma.com.ar/oauth/token/")
                self.assertEqual(parse_qs(token_request.data.decode("ascii")), {
                    "client_id": ["demo-id"], "client_secret": ["demo secret+&"],
                    "grant_type": ["client_credentials"], "scope": [scope],
                })
                url = urlsplit(data_request.full_url)
                params = parse_qs(url.query)
                self.assertEqual(url.path, path)
                self.assertEqual(params["group"], ["OBLIGACIONESNEGOC"])
                self.assertEqual(params["settlperiod"], ["0002"])
                self.assertEqual(params.get("page"), ["0"] if name == "eod" else None)
                self.assertEqual(data_request.get_header("Authorization"), "Bearer demo-token")
                self.assertIsNone(data_request.data)
                self.assertEqual(response.body, self.body)
                self.assertEqual(response.received_at.tzinfo, timezone.utc)

    def test_other_read_operations_preserve_response(self):
        cases = (
            ("placements", "/byma-primarias-placements/v1/historical-placements.json/", {"page": "1"}),
            ("dollar-eod", "/indice-dolar-byma/v1/eod.json/", {"date": "2026-11-17"}),
            ("dollar-intraday", "/indice-dolar-byma/v1/intraday.json/", {}),
            ("instruments", "/market-data-instruments/v1/fixedincome.json/", {}),
            ("news", "/market-data-news/v1/relevant-events.json/", {}),
            ("economic-indicators", "/economic-indicators/v1/principales-variables/variables.json/", {}),
            ("economic-series", "/economic-indicators/v1/principales-variables/variables/1.json/", {
                "id": "1", "from": "2026-11-02", "to": "2026-11-17",
            }),
        )
        for name, path, parameters in cases:
            with self.subTest(operation=name):
                response = self.client.fetch(name, parameters)
                url = urlsplit(self.requests[-1].full_url)
                self.assertEqual(url.path, path)
                self.assertNotIn("id", parse_qs(url.query))
                self.assertEqual(response.body, self.body)

    def test_indices_accept_csv_and_reject_json_error(self):
        params = {"fromdate": "2026-11-02", "todate": "2026-11-17"}
        self.body = b"date,value\n2026-11-02,25.9\n"
        response = self.client.fetch("indices", params)
        self.assertEqual(response.body, self.body)
        self.assertEqual(response.format, "CSV")
        self.assertEqual(self.requests[-1].get_header("Accept"), "text/csv")
        intraday = self.client.fetch("indices-intraday")
        self.assertEqual(intraday.body, self.body)
        self.assertEqual(urlsplit(self.requests[-1].full_url).path, "/byma-indices/v1/caucion/intraday.csv/")
        self.assertEqual(parse_qs(self.requests[-2].data.decode("ascii"))["scope"], ["indicesByma.intraday.read"])
        self.body = b'{"error":"Service unavailable"}'
        with self.assertRaises(ProviderResponseError):
            self.client.fetch("indices", params)

    def test_invalid_inputs_and_missing_configuration_stop_before_network(self):
        with self.assertRaises(ConfigurationError):
            self.client.fetch("economic-series", {"id": "../1", "from": "2026-11-02", "to": "2026-11-17"})
        with self.assertRaises(ConfigurationError):
            self.client.fetch("indices", {"fromdate": "2026-11-17", "todate": "2026-11-02"})
        with patch.dict(os.environ, {"BYMA_CLIENT_SECRET": ""}):
            with self.assertRaisesRegex(ConfigurationError, "BYMA_CLIENT_SECRET"):
                self.client.fetch("placements")
        self.assertEqual(self.requests, [])

    def test_invalid_token_stops_and_error_omits_response(self):
        self.token = b'{"access_token":"dummy secret"}'
        with self.assertRaises(ProviderAuthError) as error:
            self.client.fetch("placements")
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn("dummy secret", str(error.exception))

    def test_data_http_statuses_distinguish_auth_from_provider_errors(self):
        url = "https://apigw.byma.com.ar/"
        with patch("market_data.providers.byma.build_opener") as opener:
            for status, error_type in ((401, ProviderAuthError), (403, ProviderAuthError), (429, ProviderResponseError)):
                with self.subTest(status=status):
                    opener.return_value.open.side_effect = HTTPError(url, status, "private response", {}, None)
                    with self.assertRaisesRegex(error_type, str(status)) as error:
                        _send(Request(url), 20)
                    self.assertNotIn("private response", str(error.exception))
