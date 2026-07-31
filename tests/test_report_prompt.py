from __future__ import annotations

from decifra.report.html_scaffold import html_scaffold, scaffold_with_chart_specs
from decifra.report.prompt import pack_messages, pack_prompt_markdown


def _sample_context(mode: str = "credit") -> dict:
    return {
        "title": "Credit report — AAA3",
        "mode": mode,
        "language": "pt",
        "include_signals": False,
        "selected_kpis": [
            {"key": "debt_to_equity", "label": "Debt / Equity"},
            {"key": "credit_score", "label": "Credit score"},
        ],
        "subjects": {"companies": ["AAA3"], "industries": []},
        "comparatives": {"companies": [], "industries": []},
        "companies": [],
        "industries": [],
        "chart_specs": [
            {
                "id": "bar_energy",
                "type": "bar",
                "title": "Energy",
                "x": ["AAA3"],
                "y": [70.0],
            }
        ],
        "disclaimer": "Research-grade.",
    }


def test_pack_messages_credit_sections() -> None:
    messages = pack_messages(_sample_context("credit"))
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "leverage" in messages[0]["content"].lower()
    assert "debt_to_equity" in messages[1]["content"]
    assert "html_scaffold" in messages[1]["content"]
    assert "#narrative" in messages[1]["content"]
    assert "plotly" in messages[1]["content"].lower()


def test_pack_messages_equity_sections() -> None:
    ctx = _sample_context("equity")
    ctx["title"] = "Equity report — AAA3"
    messages = pack_messages(ctx)
    system = messages[0]["content"].lower()
    assert "profitability" in system or "roe" in system
    assert "leverage" not in system or "profitability" in system


def test_pack_prompt_markdown_contains_markers() -> None:
    md = pack_prompt_markdown(_sample_context())
    assert "## System" in md
    assert "## User" in md
    assert "interactive HTML" in md
    assert "DECIFRA_CHART_SPECS" in md or "chart_specs" in md


def test_html_scaffold_slots() -> None:
    html = html_scaffold("Test", language="en")
    assert 'lang="en"' in html
    assert 'id="narrative"' in html
    assert 'id="tables"' in html
    assert 'id="charts"' in html
    assert "plotly" in html.lower()

    filled = scaffold_with_chart_specs(
        "Test",
        [{"id": "c1", "type": "bar", "x": ["A"], "y": [1]}],
        language="pt",
    )
    assert "DECIFRA_CHART_SPECS" in filled
    assert '"id": "c1"' in filled or '"id":"c1"' in filled
