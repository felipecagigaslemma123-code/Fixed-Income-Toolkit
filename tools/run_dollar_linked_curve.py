"""EXPLORATORY PROTOTYPE runner — dollar-linked (LELINK) yield curve.

UNVALIDATED. Builds an illustrative yield curve for the active dollar-linked
Treasury letras and writes an HTML table and an XLSX workbook to ``outputs/``.

Governance: see ``docs/research/006_dollar_linked_letras.md`` (R-006, Under
Review). This is not production output.

Instrument dates are REAL, taken from the official Secretaría de Finanzas
colocaciones workbooks in ``data/``. Secondary-market prices are NOT available in
the repository, so this runner uses the observed **issue price** as an explicit
PLACEHOLDER. Replace ``PLACEHOLDER_PRICES`` with real A3 secondary-market prices
before drawing any conclusion. The devaluation assumption for the peso leg is a
USER INPUT (``--deval``), defaulting to 20% annual purely as an illustration.

Usage:
    python tools/run_dollar_linked_curve.py --valuation 2026-08-20 --deval 0.20
"""

from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dollar_linked_prototype import (
    DollarLinkedInput,
    DollarLinkedResult,
    build_curve,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = REPO_ROOT / "outputs"


@dataclass(frozen=True)
class ActiveInstrument:
    """Real LELINK contractual data + placeholder secondary price."""

    name: str
    issue_date: dt.date
    maturity_date: dt.date
    placeholder_price: Decimal  # observed issue price per VN 100 (PLACEHOLDER)


# Real, deduplicated active LELINK instruments (maturity > 2026-08-20),
# sourced from data/colocaciones_*.xlsx (Secretaría de Finanzas).
# placeholder_price = observed issue price per 100 (NOT a secondary-market price).
ACTIVE_INSTRUMENTS: list[ActiveInstrument] = [
    ActiveInstrument("LELINK/U$D/31-08-2026", dt.date(2026, 6, 12),
                     dt.date(2026, 8, 31), Decimal("98.97")),
    ActiveInstrument("LELINK/U$D/30-09-2026", dt.date(2026, 3, 16),
                     dt.date(2026, 9, 30), Decimal("98.97")),
    ActiveInstrument("LELINK/U$D/31-03-2027", dt.date(2026, 5, 29),
                     dt.date(2027, 3, 31), Decimal("95.61")),
]

# Par redemption (100) in USD-linked units: LELINK are zero-coupon "a descuento",
# "íntegra al vencimiento" per Res. Conjunta SF/SH 31/2025 (see R-006). The peso
# maturity payoff = VN x A3500(3rd business day before maturity); this prototype's
# peso leg approximates that FX over the full residual horizon via --deval, a
# documented simplification immaterial to a scenario tool.
REDEMPTION_VALUE = Decimal("100")


def _settlement_date(valuation: dt.date) -> dt.date:
    """T+1 MVP convention (docs/market_conventions.md), calendar-day approximation."""
    return valuation + dt.timedelta(days=1)


def build_inputs(valuation: dt.date, deval: Decimal) -> list[DollarLinkedInput]:
    settlement = _settlement_date(valuation)
    inputs: list[DollarLinkedInput] = []
    for ins in ACTIVE_INSTRUMENTS:
        if ins.maturity_date <= settlement:
            continue
        inputs.append(
            DollarLinkedInput(
                instrument=ins.name,
                market_price=ins.placeholder_price,
                settlement_date=settlement,
                maturity_date=ins.maturity_date,
                redemption_value=REDEMPTION_VALUE,
                expected_annual_devaluation=deval,
            )
        )
    return inputs


def _pct(x: Decimal) -> str:
    return f"{(x * 100):.2f}%"


def print_table(results: list[DollarLinkedResult]) -> None:
    header = (
        f"{'Instrumento':<22}{'Días':>6}{'HPR link':>10}{'TEM link':>10}"
        f"{'TNA link':>10}{'TEA link':>10}{'TEA $':>10}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.instrument:<22}{r.residual_days_actual:>6}"
            f"{_pct(r.hpr_linked):>10}{_pct(r.tem_linked):>10}"
            f"{_pct(r.tna_linked):>10}{_pct(r.tea_linked):>10}"
            f"{_pct(r.tea_pesos):>10}"
        )


def write_html(results: list[DollarLinkedResult], valuation: dt.date,
               deval: Decimal, path: Path) -> None:
    rows = "\n".join(
        f"<tr><td class='name'>{r.instrument}</td>"
        f"<td>{r.residual_days_actual}</td>"
        f"<td>{_pct(r.hpr_linked)}</td><td>{_pct(r.tem_linked)}</td>"
        f"<td>{_pct(r.tna_linked)}</td><td>{_pct(r.tea_linked)}</td>"
        f"<td class='sep'>{_pct(r.hpr_pesos)}</td><td>{_pct(r.tem_pesos)}</td>"
        f"<td>{_pct(r.tna_pesos)}</td><td>{_pct(r.tea_pesos)}</td></tr>"
        for r in results
    )
    points = ",".join(
        f"{{x:{r.residual_days_actual},link:{float(r.tea_linked) * 100:.4f},"
        f"pes:{float(r.tea_pesos) * 100:.4f},name:'{r.instrument}'}}"
        for r in results
    )
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Curva dollar-linked (PROTOTIPO)</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:24px;color:#1a1a1a;background:#fafafa}}
 .banner{{background:#fff4e5;border:1px solid #ffb74d;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:13px;color:#7a4f01}}
 h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#666;font-size:13px;margin-bottom:18px}}
 table{{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:13px}}
 th,td{{padding:8px 10px;text-align:right;border-bottom:1px solid #eee}}
 th{{background:#f0f2f5;font-weight:600}} td.name{{text-align:left;font-family:monospace}}
 td.sep,th.sep{{border-left:2px solid #ccc}}
 .grp{{background:#e8eef6}} .grp.pes{{background:#f6ece8}}
 svg{{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-top:20px}}
 .foot{{color:#888;font-size:11px;margin-top:16px;line-height:1.5}}
</style></head><body>
<div class="banner"><b>PROTOTIPO NO VALIDADO — R-006 Under Review.</b> Convención
linked = hipótesis (ACT/365 estilo IAMC). Precios = <b>PLACEHOLDER (precio de
emisión)</b>, no precios de mercado. Columna en pesos = supuesto de devaluación
del oficial ({_pct(deval)} anual), gobernado por R-009. No es salida de producción.</div>
<h1>Curva de rendimientos — Letras vinculadas al dólar (LELINK)</h1>
<div class="sub">Fecha de valuación: {valuation.isoformat()} · Liquidación T+1 ·
Rescate: {REDEMPTION_VALUE} (par) · Supuesto devaluación oficial: {_pct(deval)} anual</div>
<table>
<thead>
<tr><th rowspan="2" style="text-align:left">Instrumento</th><th rowspan="2">Días</th>
<th class="grp" colspan="4">En dólares (linked)</th>
<th class="grp pes sep" colspan="4">En pesos (con devaluación)</th></tr>
<tr><th class="grp">HPR</th><th class="grp">TEM</th><th class="grp">TNA</th><th class="grp">TEA</th>
<th class="grp pes sep">HPR</th><th class="grp pes">TEM</th><th class="grp pes">TNA</th><th class="grp pes">TEA</th></tr>
</thead>
<tbody>
{rows}
</tbody></table>
<svg id="chart" width="720" height="340" viewBox="0 0 720 340"></svg>
<div class="foot">
Fuente de datos contractuales: Secretaría de Finanzas, Colocaciones de Títulos
Públicos (data/colocaciones_*.xlsx). Instrumentos y fechas reales. Los precios son
placeholders del precio de emisión y deben reemplazarse por precios de A3 antes de
interpretar la curva. Metodología y estado: docs/research/006_dollar_linked_letras.md.
</div>
<script>
const P=[{points}];
const svg=document.getElementById('chart');
const W=720,H=340,m={{l:55,r:20,t:25,b:45}};
const xs=P.map(p=>p.x), all=P.flatMap(p=>[p.link,p.pes]);
const xmin=Math.min(...xs),xmax=Math.max(...xs);
const ymin=Math.min(...all,0),ymax=Math.max(...all);
const X=x=>m.l+(xmax===xmin?0.5:(x-xmin)/(xmax-xmin))*(W-m.l-m.r);
const Y=y=>H-m.b-(ymax===ymin?0.5:(y-ymin)/(ymax-ymin))*(H-m.t-m.b);
function ns(t,a){{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(k in a)e.setAttribute(k,a[k]);return e;}}
[0,0.25,0.5,0.75,1].forEach(f=>{{const yv=ymin+f*(ymax-ymin);const y=Y(yv);
 svg.appendChild(ns('line',{{x1:m.l,y1:y,x2:W-m.r,y2:y,stroke:'#eee'}}));
 const t=ns('text',{{x:m.l-8,y:y+4,'text-anchor':'end','font-size':11,fill:'#888'}});t.textContent=(yv).toFixed(1)+'%';svg.appendChild(t);}});
function series(key,color){{let d='';P.forEach((p,i)=>{{d+=(i?'L':'M')+X(p.x)+' '+Y(p[key])+' ';}});
 svg.appendChild(ns('path',{{d:d,fill:'none',stroke:color,'stroke-width':2.5}}));
 P.forEach(p=>{{svg.appendChild(ns('circle',{{cx:X(p.x),cy:Y(p[key]),r:4,fill:color}}));}});}}
series('link','#1565c0');series('pes','#c1440e');
P.forEach(p=>{{const t=ns('text',{{x:X(p.x),y:H-m.b+16,'text-anchor':'middle','font-size':10,fill:'#666'}});t.textContent=p.x+'d';svg.appendChild(t);}});
const lg=[['TEA en dólares (linked)','#1565c0',0],['TEA en pesos (con deval.)','#c1440e',210]];
lg.forEach(([txt,c,dx])=>{{svg.appendChild(ns('rect',{{x:m.l+dx,y:6,width:12,height:12,fill:c,rx:2}}));
 const t=ns('text',{{x:m.l+dx+18,y:16,'font-size':11,fill:'#444'}});t.textContent=txt;svg.appendChild(t);}});
</script>
</body></html>"""
    path.write_text(html, encoding="utf-8")


def write_xlsx(results: list[DollarLinkedResult], valuation: dt.date,
               deval: Decimal, path: Path) -> None:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Curva LELINK"

    warn = ("PROTOTIPO NO VALIDADO — R-006 Under Review. Convención linked = "
            "hipótesis. Precios = PLACEHOLDER (precio de emisión). Columna pesos "
            f"= supuesto devaluación {float(deval) * 100:.1f}% anual (R-009). "
            "No es salida de producción.")
    ws["A1"] = warn
    ws["A1"].font = Font(bold=True, color="7A4F01")
    ws["A1"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A1:J1")
    ws.row_dimensions[1].height = 46
    ws["A2"] = (f"Valuación: {valuation.isoformat()} · Liquidación T+1 · "
                f"Rescate {REDEMPTION_VALUE} (par)")

    headers = ["Instrumento", "Días",
               "HPR linked", "TEM linked", "TNA linked", "TEA linked",
               "HPR pesos", "TEM pesos", "TNA pesos", "TEA pesos"]
    hrow = 4
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=hrow, column=c, value=h)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="E8EEF6" if c <= 6 else "F6ECE8")
    for i, r in enumerate(results, start=hrow + 1):
        ws.cell(row=i, column=1, value=r.instrument)
        ws.cell(row=i, column=2, value=r.residual_days_actual)
        vals = [r.hpr_linked, r.tem_linked, r.tna_linked, r.tea_linked,
                r.hpr_pesos, r.tem_pesos, r.tna_pesos, r.tea_pesos]
        for c, v in enumerate(vals, start=3):
            cell = ws.cell(row=i, column=c, value=float(v))
            cell.number_format = "0.00%"
    ws.column_dimensions["A"].width = 24
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 12
    wb.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dollar-linked (LELINK) yield curve prototype")
    parser.add_argument("--valuation", default="2026-08-20", help="YYYY-MM-DD")
    parser.add_argument("--deval", default="0.20",
                        help="Assumed effective annual devaluation of the official FX (decimal)")
    args = parser.parse_args()

    valuation = dt.date.fromisoformat(args.valuation)
    deval = Decimal(args.deval)

    inputs = build_inputs(valuation, deval)
    results = build_curve(inputs)

    print(f"\nValuación: {valuation.isoformat()}  ·  Devaluación supuesta: {float(deval)*100:.1f}% anual")
    print("PROTOTIPO NO VALIDADO (R-006). Precios = placeholder (precio de emisión).\n")
    print_table(results)

    OUTPUTS_DIR.mkdir(exist_ok=True)
    html_path = OUTPUTS_DIR / "dollar_linked_curve.html"
    xlsx_path = OUTPUTS_DIR / "dollar_linked_curve.xlsx"
    write_html(results, valuation, deval, html_path)
    write_xlsx(results, valuation, deval, xlsx_path)
    print(f"\nEscrito: {html_path}")
    print(f"Escrito: {xlsx_path}")


if __name__ == "__main__":
    main()
