"""Pack ReportContext into LLM system/user messages for interactive HTML reports."""

from __future__ import annotations

import json
from typing import Any

from decifra.report.html_scaffold import scaffold_with_chart_specs


def _system_prompt(mode: str, language: str) -> str:
    lang_line = (
        "Responda em português do Brasil."
        if language == "pt"
        else "Respond in English."
    )
    if mode == "equity":
        sections = (
            "Focus sections: profitability, margins, ROE/returns, peer relative "
            "fundamentals. Do not invent valuation multiples, target prices, or DCF "
            "unless explicitly present in the context."
        )
    else:
        sections = (
            "Focus sections: leverage, liquidity, interest coverage, cash-flow "
            "coverage, credit score vs peers, and qualitative risk signals when present."
        )
    return (
        "You are a Brazilian capital-markets research analyst building an interactive "
        "HTML research report from structured local CVM data.\n"
        f"{lang_line}\n"
        "Rules:\n"
        "- Use ONLY the provided context JSON. If a datapoint is missing, say so.\n"
        "- Output ONE complete self-contained HTML document (no markdown fences).\n"
        "- Start from the provided HTML scaffold: keep CSS variables, Plotly CDN, "
        "and the section ids (#narrative, #tables, #charts, #signals, #disclaimer).\n"
        "- Fill narrative, tables, and charts. Render interactive charts with Plotly "
        "using window.DECIFRA_CHART_SPECS (and extend if useful).\n"
        "- Include the research-grade disclaimer from context.\n"
        "- This is not a bureau credit rating or investment recommendation.\n"
        f"{sections}"
    )


def pack_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for report HTML generation."""
    mode = str(context.get("mode") or "credit")
    language = str(context.get("language") or "pt")
    title = str(context.get("title") or "Decifra report")
    scaffold = scaffold_with_chart_specs(
        title,
        list(context.get("chart_specs") or []),
        language=language,
    )
    user_payload = {
        "instruction": (
            "Produce the final interactive HTML report. Fill the scaffold slots "
            "using the context below."
        ),
        "context": context,
        "html_scaffold": scaffold,
    }
    return [
        {"role": "system", "content": _system_prompt(mode, language)},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
        },
    ]


def pack_prompt_markdown(context: dict[str, Any]) -> str:
    """Human-readable prompt file (always exported; usable without API key)."""
    messages = pack_messages(context)
    parts = [
        f"# Decifra report prompt — {context.get('title', '')}",
        "",
        "## System",
        "",
        messages[0]["content"],
        "",
        "## User",
        "",
        "```json",
        messages[1]["content"],
        "```",
        "",
        "## Expected output",
        "",
        "A single self-contained interactive HTML document (Plotly charts allowed).",
        "",
    ]
    return "\n".join(parts)
