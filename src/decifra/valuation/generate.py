"""Write valuation artifacts: spec.json, context.json, valuation.md."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decifra.config import VALUATIONS_DIR, ensure_dirs
from decifra.valuation.assemble import assemble_context
from decifra.valuation.spec import ValuationSpec


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s[:60] or "valuation"


def valuation_dir(slug: str) -> Path:
    ensure_dirs()
    path = VALUATIONS_DIR / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fmt_money(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_pct(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.1%}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_num(v: Any, digits: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return str(v)


def render_valuation_markdown(context: dict[str, Any]) -> str:
    """Offline markdown summary — no LLM required, safe to regenerate any time."""
    dcf = context.get("dcf") or {}
    multiples = context.get("multiples")
    lines: list[str] = [f"# {context.get('title')}", ""]

    lines.append(f"**Ticker:** {context.get('ticker')}")
    if context.get("comparatives"):
        lines.append(f"**Comparatives:** {', '.join(context['comparatives'])}")
    lines.append("")
    lines.append(context.get("disclaimer", ""))
    lines.append("")

    lines.append("## DCF (FCFF / WACC)")
    lines.append("")
    lines.append(f"- WACC: {_fmt_pct(dcf.get('wacc'))} ({dcf.get('wacc_source')})")
    lines.append(f"- Cost of equity: {_fmt_pct(dcf.get('cost_of_equity'))}")
    lines.append(f"- After-tax cost of debt: {_fmt_pct(dcf.get('after_tax_cost_of_debt'))}")
    lines.append(f"- Enterprise value: {_fmt_money(dcf.get('enterprise_value'))}")
    lines.append(f"- Net debt: {_fmt_money(dcf.get('net_debt'))}")
    lines.append(f"- Equity value: {_fmt_money(dcf.get('equity_value'))}")
    lines.append(f"- Value per share: {_fmt_num(dcf.get('value_per_share'))}")
    lines.append(f"- Current price: {_fmt_num(dcf.get('current_price'))}")
    lines.append(f"- Upside/downside: {_fmt_pct(dcf.get('upside_pct'))}")
    try:
        upside = float(dcf["upside_pct"]) if dcf.get("upside_pct") is not None else None
    except (TypeError, ValueError):
        upside = None
    if upside is not None and abs(upside) > 1.0:
        lines.append("")
        lines.append(
            "> **Note:** Defaults are a starting point, not a price target. "
            f"Implied upside/downside of {_fmt_pct(upside)} is extreme — "
            "revisit growth, margins, WACC, and scale before acting."
        )
    if dcf.get("warnings"):
        lines.append("")
        lines.append("**Warnings:**")
        for w in dcf["warnings"]:
            lines.append(f"- {w}")
    lines.append("")

    years = dcf.get("years") or []
    if years:
        lines.append("| Year | Growth | Revenue | EBIT | FCFF | PV(FCFF) |")
        lines.append("|---|---|---|---|---|---|")
        for y in years:
            lines.append(
                f"| {y.get('year')} | {_fmt_pct(y.get('growth'))} | {_fmt_money(y.get('revenue'))} | "
                f"{_fmt_money(y.get('ebit'))} | {_fmt_money(y.get('fcff'))} | {_fmt_money(y.get('pv_fcff'))} |"
            )
        lines.append("")

    if multiples:
        lines.append("## Trading multiples (relative valuation)")
        lines.append("")
        lines.append(f"- Peer stat: {multiples.get('stat')} across {multiples.get('peer_count')} comparable(s)")
        subj = multiples.get("subject") or {}
        peer_mult = multiples.get("peer_multiples") or {}
        implied = multiples.get("implied_price") or {}
        lines.append("| Multiple | Subject | Peer | Implied price |")
        lines.append("|---|---|---|---|")
        for key, label in (
            ("pe", "P/E"),
            ("ev_ebitda", "EV/EBITDA"),
            ("ev_revenue", "EV/Revenue"),
            ("ev_ebit", "EV/EBIT"),
            ("pb", "P/B"),
        ):
            lines.append(
                f"| {label} | {_fmt_num(subj.get(key))} | {_fmt_num(peer_mult.get(key))} | "
                f"{_fmt_num(implied.get(key))} |"
            )
        lines.append("")
        lines.append(
            f"Implied price range: {_fmt_num(multiples.get('implied_price_low'))} – "
            f"{_fmt_num(multiples.get('implied_price_high'))} "
            f"(avg {_fmt_num(multiples.get('implied_price_avg'))})"
        )
        if multiples.get("warnings"):
            lines.append("")
            for w in multiples["warnings"]:
                lines.append(f"- {w}")
        lines.append("")

    lines.append("## How these numbers were built")
    lines.append("")
    for note in context.get("methodology") or []:
        lines.append(f"- **{note.get('label')}** = {_fmt_num(note.get('value'), 4)}")
        lines.append(f"  - Formula: {note.get('formula')}")
        lines.append(f"  - {note.get('rationale')}")
    lines.append("")

    return "\n".join(lines)


def build_valuation_artifacts(
    spec: ValuationSpec, *, out_dir: Path | None = None
) -> dict[str, Any]:
    """Assemble context and write spec.json, context.json, valuation.md."""
    context = assemble_context(spec)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"{_slugify(spec.default_title())}-{stamp}"
    dest = out_dir or valuation_dir(slug)
    dest.mkdir(parents=True, exist_ok=True)

    spec_path = dest / "spec.json"
    context_path = dest / "context.json"
    markdown_path = dest / "valuation.md"

    spec_path.write_text(json.dumps(spec.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = render_valuation_markdown(context)
    markdown_path.write_text(markdown, encoding="utf-8")

    return {
        "ok": True,
        "dir": str(dest),
        "slug": dest.name,
        "spec_path": str(spec_path),
        "context_path": str(context_path),
        "markdown_path": str(markdown_path),
        "context": context,
        "markdown": markdown,
    }
