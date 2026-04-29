"""HTML report generator for experiment results.

Reads the JSONL ledger and produces a self-contained HTML report with
Plotly charts embedded inline — no external dependencies at render time.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING, Any

import structlog

from a2a.exceptions import ReportError

if TYPE_CHECKING:
    from pathlib import Path

log = structlog.get_logger(__name__)


class ReportGenerator:
    """Generate a self-contained HTML report from a completed experiment directory."""

    def __init__(self, experiment_dir: Path) -> None:
        self._dir = experiment_dir
        self._ledger_path = experiment_dir / "results.jsonl"
        self._summary_path = experiment_dir / "summary.json"

        if not self._ledger_path.exists():
            raise ReportError(f"Ledger not found: {self._ledger_path}")

    def build(self) -> Path:
        records = self._load_records()
        summary = self._load_summary()
        html = self._render(records, summary)
        out = self._dir / "report.html"
        out.write_text(html, encoding="utf-8")
        log.info("report_built", path=str(out), dyads=len(records))
        return out

    def _load_records(self) -> list[dict[str, Any]]:
        records = []
        with self._ledger_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _load_summary(self) -> dict[str, Any]:
        if self._summary_path.exists():
            return json.loads(self._summary_path.read_text(encoding="utf-8"))
        return {}

    def _render(self, records: list[dict[str, Any]], summary: dict[str, Any]) -> str:
        slug = summary.get("slug", self._dir.name)
        product_type = summary.get("product_type", "")
        buy_rate = summary.get("buy_rate", 0.0)
        total_cost = summary.get("total_cost_usd", 0.0)
        avg_latency = summary.get("avg_latency_ms", 0.0)
        total_dyads = summary.get("total_dyads", len(records))

        # Build chart data
        outcomes = Counter(r.get("outcome", "unknown") for r in records)
        funnel_variants = sorted({r.get("funnel_variant", "") for r in records})
        archetypes = sorted({r.get("buyer_archetype", "") for r in records})

        # Buy rate by funnel variant
        variant_buy_rates: dict[str, float] = {}
        for v in funnel_variants:
            subset = [r for r in records if r.get("funnel_variant") == v]
            if subset:
                variant_buy_rates[v] = sum(1 for r in subset if r.get("outcome") == "buy") / len(subset)

        # Buy rate by archetype
        archetype_buy_rates: dict[str, float] = {}
        for a in archetypes:
            subset = [r for r in records if r.get("buyer_archetype") == a]
            if subset:
                archetype_buy_rates[a] = sum(1 for r in subset if r.get("outcome") == "buy") / len(subset)

        # Avg negotiation turns by outcome
        avg_turns = {
            outcome: (
                sum(r.get("negotiation_turns_used", 0) for r in records if r.get("outcome") == outcome)
                / max(1, sum(1 for r in records if r.get("outcome") == outcome))
            )
            for outcome in outcomes
        }

        # Cost distribution
        costs = [r.get("total_cost_usd", 0.0) for r in records]
        latencies = [r.get("total_latency_ms", 0.0) for r in records]

        charts_data = json.dumps({
            "outcomes": dict(outcomes),
            "variant_buy_rates": variant_buy_rates,
            "archetype_buy_rates": archetype_buy_rates,
            "avg_turns_by_outcome": avg_turns,
            "costs": costs,
            "latencies": latencies,
        })

        # Sample dyad traces (first 5)
        records[:5]
        dyad_rows = "".join(
            f"""<tr class="{'bg-green-950' if d.get('outcome') == 'buy' else 'bg-neutral-900'}">
  <td class="px-3 py-2 font-mono text-xs">{d.get('dyad_id','')}</td>
  <td class="px-3 py-2 text-xs">{d.get('buyer_archetype','')}</td>
  <td class="px-3 py-2 text-xs">{d.get('funnel_variant','')}</td>
  <td class="px-3 py-2 font-bold {'text-green-400' if d.get('outcome') == 'buy' else 'text-red-400'}">{d.get('outcome','')}</td>
  <td class="px-3 py-2 text-xs">${d.get('agreed_price_usd') or '—'}</td>
  <td class="px-3 py-2 text-xs">{d.get('negotiation_turns_used',0)}</td>
  <td class="px-3 py-2 text-xs">${d.get('total_cost_usd',0):.5f}</td>
  <td class="px-3 py-2 text-xs">{d.get('total_latency_ms',0):.0f}ms</td>
</tr>"""
            for d in records[:20]
        )

        # Judge score table (first 5 with scores)
        judge_rows = ""
        scored = [r for r in records if r.get("judge_score") and "buyer" in r.get("judge_score", {})][:5]
        for d in scored:
            jb = d["judge_score"].get("buyer", {})
            js = d["judge_score"].get("seller", {})
            judge_rows += f"""<tr class="border-b border-neutral-800">
  <td class="px-3 py-2 font-mono text-xs">{d.get('dyad_id','')}</td>
  <td class="px-3 py-2 text-xs">{d.get('outcome','')}</td>
  <td class="px-3 py-2 text-center">{jb.get('total', '—')}</td>
  <td class="px-3 py-2 text-center">{js.get('total', '—')}</td>
  <td class="px-3 py-2 text-xs text-neutral-400">{jb.get('notes', '')[:80]}</td>
</tr>"""

        return f"""<!DOCTYPE html>
<html lang="en" class="bg-neutral-950 text-neutral-100">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>a2a Experiment Report — {slug}</title>
  <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ font-family: 'Inter', system-ui, sans-serif; }}
    .chart {{ min-height: 280px; }}
  </style>
</head>
<body class="min-h-screen bg-neutral-950 text-neutral-100">

<div class="max-w-7xl mx-auto px-6 py-10">

  <!-- Hero -->
  <div class="mb-10">
    <div class="text-xs text-neutral-500 uppercase tracking-widest mb-2">a2a experiment report</div>
    <h1 class="text-3xl font-bold mb-1">{slug}</h1>
    <p class="text-neutral-400 text-sm">{product_type.replace('_',' ').title()} · {total_dyads} dyads</p>
  </div>

  <!-- KPI row -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
    <div class="bg-neutral-900 rounded-xl p-5">
      <div class="text-neutral-400 text-xs mb-1">Buy rate</div>
      <div class="text-4xl font-bold text-green-400">{buy_rate:.1%}</div>
    </div>
    <div class="bg-neutral-900 rounded-xl p-5">
      <div class="text-neutral-400 text-xs mb-1">Total LLM cost</div>
      <div class="text-4xl font-bold">${total_cost:.4f}</div>
    </div>
    <div class="bg-neutral-900 rounded-xl p-5">
      <div class="text-neutral-400 text-xs mb-1">Avg latency</div>
      <div class="text-4xl font-bold">{avg_latency:.0f}<span class="text-lg text-neutral-400">ms</span></div>
    </div>
    <div class="bg-neutral-900 rounded-xl p-5">
      <div class="text-neutral-400 text-xs mb-1">Dyads</div>
      <div class="text-4xl font-bold">{total_dyads}</div>
    </div>
  </div>

  <!-- Charts row 1 -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <div class="bg-neutral-900 rounded-xl p-5">
      <h2 class="text-sm font-semibold text-neutral-300 mb-3">Outcome distribution</h2>
      <div id="chart-outcomes" class="chart"></div>
    </div>
    <div class="bg-neutral-900 rounded-xl p-5">
      <h2 class="text-sm font-semibold text-neutral-300 mb-3">Buy rate by seller funnel variant</h2>
      <div id="chart-funnel-variant" class="chart"></div>
    </div>
  </div>

  <!-- Charts row 2 -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <div class="bg-neutral-900 rounded-xl p-5">
      <h2 class="text-sm font-semibold text-neutral-300 mb-3">Buy rate by buyer archetype</h2>
      <div id="chart-archetype" class="chart"></div>
    </div>
    <div class="bg-neutral-900 rounded-xl p-5">
      <h2 class="text-sm font-semibold text-neutral-300 mb-3">Cost per dyad (USD) distribution</h2>
      <div id="chart-cost" class="chart"></div>
    </div>
  </div>

  <!-- Dyad table -->
  <div class="bg-neutral-900 rounded-xl p-5 mb-8">
    <h2 class="text-sm font-semibold text-neutral-300 mb-3">Dyad records (first 20)</h2>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-neutral-400 text-xs border-b border-neutral-800">
            <th class="px-3 py-2 text-left">ID</th>
            <th class="px-3 py-2 text-left">Buyer archetype</th>
            <th class="px-3 py-2 text-left">Funnel variant</th>
            <th class="px-3 py-2 text-left">Outcome</th>
            <th class="px-3 py-2 text-left">Price</th>
            <th class="px-3 py-2 text-left">Turns</th>
            <th class="px-3 py-2 text-left">Cost</th>
            <th class="px-3 py-2 text-left">Latency</th>
          </tr>
        </thead>
        <tbody>{dyad_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- Judge scores -->
  {f'''<div class="bg-neutral-900 rounded-xl p-5 mb-8">
    <h2 class="text-sm font-semibold text-neutral-300 mb-3">Judge LLM rationale scores</h2>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-neutral-400 text-xs border-b border-neutral-800">
            <th class="px-3 py-2 text-left">Dyad</th>
            <th class="px-3 py-2 text-left">Outcome</th>
            <th class="px-3 py-2 text-center">Buyer score</th>
            <th class="px-3 py-2 text-center">Seller score</th>
            <th class="px-3 py-2 text-left">Notes</th>
          </tr>
        </thead>
        <tbody>{judge_rows}</tbody>
      </table>
    </div>
  </div>''' if judge_rows else ''}

  <!-- Footer -->
  <div class="text-neutral-600 text-xs text-center pt-6 border-t border-neutral-800">
    Generated by <a href="https://github.com/chernov-consulting/a2a" class="underline">chernov-consulting/a2a</a>
    · <a href="https://a2a.chernov.io" class="underline">a2a.chernov.io</a>
    · Apache-2.0 / CC-BY-4.0
  </div>
</div>

<script>
const data = {charts_data};
const dark = {{ paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: {{ color: '#d4d4d4' }}, margin: {{ t: 10, b: 40, l: 50, r: 20 }} }};

// Outcome pie
Plotly.newPlot('chart-outcomes', [{{
  type: 'pie',
  labels: Object.keys(data.outcomes),
  values: Object.values(data.outcomes),
  marker: {{ colors: ['#4ade80', '#f87171', '#facc15', '#94a3b8'] }},
  hole: 0.4,
}}], {{ ...dark, showlegend: true }});

// Funnel variant buy rate
Plotly.newPlot('chart-funnel-variant', [{{
  type: 'bar',
  x: Object.keys(data.variant_buy_rates),
  y: Object.values(data.variant_buy_rates).map(v => +(v * 100).toFixed(1)),
  marker: {{ color: '#818cf8' }},
}}], {{ ...dark, yaxis: {{ title: 'Buy rate (%)', tickformat: '.1f' }} }});

// Archetype buy rate
Plotly.newPlot('chart-archetype', [{{
  type: 'bar',
  x: Object.keys(data.archetype_buy_rates),
  y: Object.values(data.archetype_buy_rates).map(v => +(v * 100).toFixed(1)),
  marker: {{ color: '#34d399' }},
}}], {{ ...dark, yaxis: {{ title: 'Buy rate (%)', tickformat: '.1f' }} }});

// Cost histogram
Plotly.newPlot('chart-cost', [{{
  type: 'histogram',
  x: data.costs,
  marker: {{ color: '#f59e0b' }},
  nbinsx: 30,
}}], {{ ...dark, xaxis: {{ title: 'Cost (USD)' }}, yaxis: {{ title: 'Dyads' }} }});
</script>
</body>
</html>"""
