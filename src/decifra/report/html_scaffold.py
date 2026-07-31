"""Minimal interactive HTML shell for LLM-filled credit/equity reports."""

from __future__ import annotations

from typing import Any


def html_scaffold(title: str, language: str = "pt") -> str:
    """Return a self-contained HTML shell with Plotly CDN and empty slots."""
    lang = "pt-BR" if language == "pt" else "en"
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(title)}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bg: #f7f5f1;
      --ink: #1a1f1c;
      --muted: #5c6560;
      --accent: #0f5c4c;
      --line: #d9d4cb;
      --card: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      background: linear-gradient(165deg, #f7f5f1 0%, #e8efe9 55%, #f7f5f1 100%);
      color: var(--ink);
      line-height: 1.5;
    }}
    header {{
      padding: 2rem 1.5rem 1rem;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.55);
    }}
    header h1 {{ margin: 0 0 0.35rem; font-size: 1.75rem; color: var(--accent); }}
    header p {{ margin: 0; color: var(--muted); max-width: 52rem; }}
    main {{ padding: 1.25rem 1.5rem 3rem; max-width: 1100px; margin: 0 auto; }}
    section {{ margin: 1.75rem 0; }}
    section h2 {{ font-size: 1.15rem; margin: 0 0 0.75rem; color: var(--accent); }}
    #narrative p {{ max-width: 48rem; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      font-size: 0.92rem;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 0.5rem 0.65rem;
      text-align: left;
    }}
    th {{ background: #eef3f0; }}
    .chart {{
      width: 100%;
      min-height: 320px;
      background: var(--card);
      border: 1px solid var(--line);
      margin-bottom: 1rem;
    }}
    footer {{
      padding: 1rem 1.5rem 2rem;
      color: var(--muted);
      font-size: 0.85rem;
      border-top: 1px solid var(--line);
    }}
  </style>
</head>
<body>
  <header>
    <h1 id="report-title">{_escape(title)}</h1>
    <p id="report-subtitle"><!-- fill: one-line scope summary --></p>
  </header>
  <main>
    <section id="narrative">
      <!-- fill: executive summary paragraphs -->
    </section>
    <section id="tables">
      <!-- fill: KPI comparison tables -->
    </section>
    <section id="charts">
      <!-- fill: div.chart nodes + Plotly.newPlot calls using chart_specs -->
    </section>
    <section id="signals">
      <!-- fill: qualitative risk signals when present; omit if empty -->
    </section>
  </main>
  <footer id="disclaimer">
    <!-- fill: research-grade disclaimer from context -->
  </footer>
  <script>
    // Chart data from context.chart_specs should be rendered here with Plotly.
    window.DECIFRA_CHART_SPECS = [];
  </script>
</body>
</html>
"""


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def scaffold_with_chart_specs(title: str, chart_specs: list[dict[str, Any]], language: str = "pt") -> str:
    """Scaffold with chart_specs embedded as JSON for the model to wire up."""
    import json

    html = html_scaffold(title, language=language)
    payload = json.dumps(chart_specs, ensure_ascii=False)
    return html.replace(
        "window.DECIFRA_CHART_SPECS = [];",
        f"window.DECIFRA_CHART_SPECS = {payload};",
    )
