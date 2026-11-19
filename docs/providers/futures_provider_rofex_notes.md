# Futures Provider — Matba Rofex / Primary (research notes)

| Field | Value |
|-------|-------|
| Document | Research notes (NOT a confirmed contract) |
| Provider | Matba Rofex / Primary |
| API type | REST + WebSocket (+ FIX), user + password + account |
| Status | 🔵 Research only — no key, not implemented |
| Owner | Felipe Cagigas |
| Last Updated | 10 August 2026 |

> **Why this is a separate document.** This venue is **distinct** from the A3 /
> MAE MarketData API (see `a3_provider_contract.md`). It uses a different
> authentication model and covers **futures**, which the MAE MarketData API does
> not. The two are intentionally not mixed in one contract.

> **Public viewer distinction.** A provisional, local-only reader for A3's
> public price viewer is documented separately in
> `a3_public_futures_viewer_contract.md`. That source supplies contract
> reference data and recent observed trades without credentials; it does not
> turn the viewer endpoints into a confirmed Primary API contract and does not
> replace this future credentialed integration.

## Summary

- **Purpose:** dollar (and other) **futures** market data and order routing.
- **Protocols:** REST + WebSocket (+ FIX).
- **Official client libraries** (maintained by Matba Rofex): `pyRofex` (Python),
  `jsRofex` (Node), `rRofex` (R).
- **Environments:** `reMarket` (free self-service demo/test) and `LIVE`
  (production credentials via the market/broker).
- **Authentication:** user + password + account → token (NOT an `x-api-key`).
- **Market-data entries** (to confirm vs docs): bid, offer, last, settlement
  price, open/close, high/low, volume, open interest.
- **Dollar futures contract:** underlying USD, contract size 1,000, cash-settled
  by differences.
- **No ready-made MCP connector** exists; integration would be via `pyRofex`
  behind a future `RofexProvider` implementing the provider Protocol.

## Status

- We do **not** have credentials for this venue yet.
- The credentialed Primary API is not implemented. If/when supported access is
  available, a separate provider will be added behind the provider protocol,
  with its own confirmed contract. Until then the public viewer prototype is
  limited to the observed fields documented in its separate contract.

Sources: `pyRofex` (github.com/matbarofex/pyRofex), A3 Mercados
(a3mercados.com.ar), Matba Rofex (matbarofex.com.ar).

---

**Version:** 1.0

**Last Updated:** 10 August 2026
