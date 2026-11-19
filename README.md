# Fixed Income Toolkit

Professional fixed-income analytics toolkit, initially focused on Argentine
Treasury instruments (LECAP / BONCAP). Developed incrementally, prioritizing
correctness, transparency and traceability over feature count: no financial
calculation reaches production until its methodology is documented and validated
against official sources.

> Status: **incremental implementation & validation.** Approved LECAP/BONCAP
> VPV, HPR, TNA, TEA, TEM and single-payment Duration components are
> implemented. Every additional formula remains independently research-gated.

For supported LECAP/BONCAP instruments, contractual VPV uses the
Treasury-adapted 30/360 convention. Residual secondary-market yields use actual
calendar days on ACT/365: `TEA = (1+HPR)^(365/D)-1`,
`TEM = (1+TEA)^(1/12)-1`, and `TNA = TEM*12`.

## Repository structure

- `docs/` — documentation (vision, scope, specification, market conventions). Source of truth.
- `docs/research/` — per-metric research notes (VPV, HPR, TNA, TEA, …) with validation status.
- `src/financial_engine/` — production calculation modules (public interfaces).
- `tools/` — development utilities (e.g. `inspect_excel.py`).
- `tests/` — automated tests.
- `examples/` — reference calculators and validation cases.
- `bibliography/` — financial references.
- `data/` — structured datasets.
- `outputs/` — generated files (inventories, exploration models).

## Requirements

- Python 3.9 or newer. The repository's included `.venv/` uses Python 3.9 and
  is the first runtime selected by the macOS launchers.
- `openpyxl` (Excel inspection and model generation).

## Setup

The repository already includes a virtual environment. Activate it:

    source .venv/bin/activate        # macOS / Linux

Optionally (re)install the declared dependencies into the active environment;
this does not replace the existing `.venv`:

    pip install -e ".[test]"

## Usage

Inspect an Excel calculator (read-only) and export an inventory:

    python tools/inspect_excel.py "examples/01_calculators/CALCULADORA - LETRAS.xlsx"

Outputs are written to `outputs/`. An interactive exploration model
(`outputs/modelo_lecap_boncap.html`, plus `outputs/Modelo_LECAP_BONCAP.xlsx`)
provides tasas, Duration and a yield curve — these are exploration tools, not the
gated production engine.

`outputs/lecap_model.html` is retained only as a historical filename and
redirects to `outputs/modelo_lecap_boncap.html`; it must not be used as an
independent calculator.

Synchronize official Treasury Bill results with A3 secondary-market visibility
(read-only; UAT by default):

    python tools/sync_treasury_bills.py

The command stages official source evidence in SQLite and marks a Letra
`ACTIVE_FOR_ANALYSIS` only after A3 exposes it in fixed income. Operational
activation does not validate any financial formula or contractual value. Use
`--environment PROD --allow-production` only for an explicitly authorized
production run.

Run the approved recurring schedule in the foreground:

    python tools/run_treasury_bill_scheduler.py

It checks Secretaría de Finanzas immediately and every 24 hours, and A3
immediately and every 15 minutes. Each A3 cycle also persists the current
Decimal-safe quote; daily history accumulates without claiming tick-by-tick
storage. UAT remains the default. The process must be kept running by a host
such as `launchd`, a server process manager or a future deployment service;
process-manager installation is intentionally separate from the repository
code.

Serve the existing LECAP/BONCAP HTML from the local SQLite database:

    python tools/serve_local_dashboard.py

The page is available only on this computer at `http://127.0.0.1:8765` and
opens in Google Chrome by default. It reads the latest A3 T+1 observations from
SQLite immediately and every 15 minutes, retains the manual refresh button and
shows Treasury lifecycle states separately from financial validation. Use
`--no-open-chrome` to start the local page without opening the browser. The
dashboard server does not contact A3 or perform financial calculations; keep
the scheduler above running to update SQLite.

For normal local use, start both processes with one command (UAT by default):

    python tools/run_local_toolkit.py

This starts the approved daily/15-minute updater, serves the same HTML and opens
it in Google Chrome. Production still requires both `--environment PROD` and the
explicit `--allow-production` acknowledgement.

On macOS, double-click `Abrir Modelo LECAP BONCAP.command` in the repository
folder. Opening `outputs/modelo_lecap_boncap.html` directly is not equivalent:
the `file://` page cannot read the local SQLite API. A manual refresh selects the
latest A3 market date available and shows an explicit warning when that date is
earlier than today. It displays HPR/TNA/TEA/TEM only when the selected purchase
date matches the price observation; dated IAMC snapshots cannot silently
generate a rate for another date.

On this Mac, `com.fixedincome.morningsync` starts the Production scheduler every
day at 09:30 local time. A3 runs immediately and then every 15 minutes;
Secretaría de Finanzas runs immediately and then every 24 hours. The scheduler
continues independently of Chrome. The macOS dashboard launcher therefore uses
`--external-scheduler` and does not start a duplicate updater. The manual HTML
refresh button remains available and rereads the latest stored SQLite data.

Start the observed dollar-futures screen separately (no credential required):

    python tools/run_futures_toolkit.py

On this Mac, the non-technical option is to double-click
`Abrir Futuros Dolar.command` in the repository folder. It selects an available
Python 3.9+ runtime, starts both local processes and opens Chrome.

This opens `http://127.0.0.1:8766/futures` in Chrome, refreshes the DLR contract
listing daily and recent public trades every 15 minutes, and keeps history in
the same local SQLite database. The source is a provisional public viewer, so
missing bid/ask, settlement, daily range and open-interest fields remain empty.
The screen contains no spot, implied-rate or forward/futures calculation; R-009
remains under review. For an on-demand one-time refresh use:

    python tools/sync_futures.py

## Testing

    pytest

Tests cover the approved maturity-value, day-count, HPR/TNA/TEA/TEM and
single-payment Duration calculations, the A3/SQLite data path, lifecycle
activation, futures observations and the dashboard temporal-alignment policy.

## Governance

Development follows `CLAUDE.md`, `docs/ai_agent.md` and
`docs/financial_specification.md`: documentation first, no invented formulas or
market conventions, and a Research Gate that must be satisfied and human-approved
before any production formula is implemented.
