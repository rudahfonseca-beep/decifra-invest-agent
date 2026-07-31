"""Offline interactive HTML renderer from context.json + chart_specs (no LLM).

Uses Jinja2 string templates and Plotly CDN to produce a self-contained
interactive report.  Keeps the same visual language as the LLM scaffold
(html_scaffold.py CSS variables).

Implements IMP-012.
"""

from __future__ import annotations

import json
from typing import Any

from jinja2 import Template

from decifra.report.catalog import PCT_KPIS, kpi_label

_TEMPLATE_STR = r"""<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {
      --bg: #f7f5f1;
      --ink: #1a1f1c;
      --muted: #5c6560;
      --accent: #0f5c4c;
      --line: #d9d4cb;
      --card: #ffffff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      background: linear-gradient(165deg, #f7f5f1 0%, #e8efe9 55%, #f7f5f1 100%);
      color: var(--ink);
      line-height: 1.5;
    }
    header {
      padding: 2rem 1.5rem 1rem;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.55);
    }
    header h1 { margin: 0 0 0.35rem; font-size: 1.75rem; color: var(--accent); }
    header p { margin: 0; color: var(--muted); max-width: 52rem; }
    main { padding: 1.25rem 1.5rem 3rem; max-width: 1100px; margin: 0 auto; }
    section { margin: 1.75rem 0; }
    section h2 { font-size: 1.15rem; margin: 0 0 0.75rem; color: var(--accent); }
    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      font-size: 0.92rem;
      margin-bottom: 1rem;
    }
    th, td {
      border: 1px solid var(--line);
      padding: 0.5rem 0.65rem;
      text-align: left;
    }
    th { background: #eef3f0; }
    .chart {
      width: 100%;
      min-height: 320px;
      background: var(--card);
      border: 1px solid var(--line);
      margin-bottom: 1rem;
    }
    footer {
      padding: 1rem 1.5rem 2rem;
      color: var(--muted);
      font-size: 0.85rem;
      border-top: 1px solid var(--line);
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }
    .kpi-card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0.75rem 1rem;
    }
    .kpi-card .label { color: var(--muted); font-size: 0.82rem; }
    .kpi-card .value { font-size: 1.25rem; font-weight: 600; color: var(--accent); }
    .signal-badge {
      display: inline-block;
      background: #fef3cd;
      color: #856404;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      font-size: 0.82rem;
      margin: 0.15rem 0.2rem;
    }
  </style>
</head>
<body>
  <header>
    <h1>{{ title }}</h1>
    <p>{{ subtitle }}</p>
  </header>
  <main>
    <!-- Company sections -->
    {% for co in companies %}
    {% if co.found %}
    <section>
      <h2>{{ co.ticker }} — {{ co.company }}</h2>
      <p style="color:var(--muted);">
        {{ co.industry_group }} · {{ co.cohort }} · Period: {{ co.period or 'N/A' }}
        {% if not co.has_financials %} · <em>No financial data</em>{% endif %}
      </p>
      <div class="kpi-grid">
        {% for key, cell in co.kpis.items() %}
        <div class="kpi-card">
          <div class="label">{{ cell.label }}</div>
          <div class="value">{{ format_value(key, cell.value) }}</div>
          {% if co.peer_medians and key in co.peer_medians %}
          <div class="label">Peer median: {{ format_value(key, co.peer_medians[key].value) }}</div>
          {% endif %}
        </div>
        {% endfor %}
      </div>
      {% if co.signals and co.signals.hit_count %}
      <p><strong>Risk signals</strong> ({{ co.signals.hit_count }} hits, penalty: {{ "%.1f"|format(co.signals.qualitative_penalty or 0) }})</p>
      {% for kw in co.signals.matched_keywords %}
      <span class="signal-badge">{{ kw }}</span>
      {% endfor %}
      {% endif %}
    </section>
    {% endif %}
    {% endfor %}

    <!-- Industry sections -->
    {% for ind in industries %}
    {% if ind.found %}
    <section>
      <h2>{{ ind.industry_group }} — Industry Overview</h2>
      <p style="color:var(--muted);">
        {{ ind.member_count }} members · {{ ind.with_financials }} with financials
      </p>
      {% if ind.peer_medians %}
      <div class="kpi-grid">
        {% for key, cell in ind.peer_medians.items() %}
        <div class="kpi-card">
          <div class="label">{{ cell.label }} (median)</div>
          <div class="value">{{ format_value(key, cell.value) }}</div>
        </div>
        {% endfor %}
      </div>
      {% endif %}
      {% if ind.ranked_members %}
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Ticker</th>
            <th>Company</th>
            <th>Score</th>
            {% for key in selected_kpi_keys[:6] %}
            <th>{{ kpi_label_fn(key) }}</th>
            {% endfor %}
          </tr>
        </thead>
        <tbody>
          {% for m in ind.ranked_members %}
          <tr>
            <td>{{ loop.index }}</td>
            <td><strong>{{ m.ticker }}</strong></td>
            <td>{{ m.company or '' }}</td>
            <td>{{ format_value('score', m.primary_score) }}</td>
            {% for key in selected_kpi_keys[:6] %}
            <td>{{ format_value(key, m.kpis[key].value if key in m.kpis else None) }}</td>
            {% endfor %}
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% endif %}
    </section>
    {% endif %}
    {% endfor %}

    <!-- Charts -->
    <section id="charts">
      <h2>Charts</h2>
      {% for chart in chart_specs %}
      <div id="chart-{{ chart.id }}" class="chart"></div>
      {% endfor %}
    </section>
  </main>

  <footer id="disclaimer">
    {{ disclaimer }}
  </footer>

  <script>
    var specs = {{ chart_specs_json }};
    specs.forEach(function(spec) {
      var el = document.getElementById('chart-' + spec.id);
      if (!el) return;
      if (spec.type === 'bar') {
        Plotly.newPlot(el, [{
          x: spec.x, y: spec.y, type: 'bar',
          marker: {color: '#0f5c4c'}
        }], {
          title: spec.title,
          margin: {t: 40, b: 40, l: 50, r: 20},
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)'
        }, {responsive: true});
      } else if (spec.type === 'grouped_bar') {
        var traces = (spec.series || []).map(function(s, i) {
          return {
            name: s.name,
            x: spec.categories,
            y: s.values,
            type: 'bar',
            marker: {color: i === 0 ? '#0f5c4c' : '#a0c4b8'}
          };
        });
        Plotly.newPlot(el, traces, {
          title: spec.title,
          barmode: 'group',
          margin: {t: 40, b: 40, l: 50, r: 20},
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)'
        }, {responsive: true});
      }
    });
  </script>
</body>
</html>"""


def _format_value(key: str, value: Any) -> str:
    """Human-readable formatting for KPI values."""
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    if key in PCT_KPIS:
        return f"{value * 100:.1f}%"
    if isinstance(value, float):
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:,.1f}M"
        if abs(value) >= 1_000:
            return f"{value / 1_000:,.1f}K"
        return f"{value:,.2f}"
    return str(value)


def render_offline_html(context: dict[str, Any]) -> str:
    """Render interactive HTML report from assembled context (no LLM)."""
    title = str(context.get("title") or "Decifra Report")
    language = str(context.get("language") or "pt")
    lang = "pt-BR" if language == "pt" else "en"

    companies = context.get("companies") or []
    industries = context.get("industries") or []
    chart_specs = context.get("chart_specs") or []
    disclaimer = context.get("disclaimer") or ""
    selected_kpis = context.get("selected_kpis") or []
    selected_kpi_keys = [k["key"] for k in selected_kpis]

    # Build subtitle
    subj = context.get("subjects") or {}
    parts = []
    if subj.get("companies"):
        parts.append(", ".join(subj["companies"]))
    if subj.get("industries"):
        parts.append(", ".join(subj["industries"]))
    mode_label = "Credit" if context.get("mode") == "credit" else "Equity"
    subtitle = f"{mode_label} analysis — {' · '.join(parts)}" if parts else f"{mode_label} analysis"

    template = Template(_TEMPLATE_STR)
    return template.render(
        title=title,
        subtitle=subtitle,
        lang=lang,
        companies=companies,
        industries=industries,
        chart_specs=chart_specs,
        chart_specs_json=json.dumps(chart_specs, ensure_ascii=False),
        disclaimer=disclaimer,
        selected_kpi_keys=selected_kpi_keys,
        kpi_label_fn=kpi_label,
        format_value=_format_value,
    )
