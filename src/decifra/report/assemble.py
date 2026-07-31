"""Assemble factual ReportContext JSON from local credit/KPI data."""

from __future__ import annotations

from typing import Any

import pandas as pd

from decifra.credit.scoring import build_credit_table, peer_medians
from decifra.credit.signals import scan_qualitative_signals
from decifra.report.catalog import PRIMARY_SCORE_BY_MODE, kpi_label
from decifra.report.spec import ReportSpec


def _json_num(v: Any) -> float | int | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (v != v):  # NaN
            return None
        return float(v) if isinstance(v, float) else int(v)
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x:
        return None
    return x


def _pick_kpis(row: pd.Series | dict[str, Any], keys: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in keys:
        if isinstance(row, pd.Series):
            val = row.get(k) if k in row.index else None
        else:
            val = row.get(k)
        out[k] = {
            "label": kpi_label(k),
            "value": _json_num(val) if not isinstance(val, str) else val,
        }
        # Prefer numeric coercion for known numeric fields
        if not isinstance(val, str):
            out[k]["value"] = _json_num(val)
    return out


def _company_block(
    df: pd.DataFrame,
    ticker: str,
    kpi_keys: list[str],
    *,
    include_signals: bool,
    role: str,
) -> dict[str, Any]:
    hits = df[df["ticker"].astype(str).str.upper() == ticker.upper()]
    if hits.empty:
        return {
            "role": role,
            "ticker": ticker.upper(),
            "found": False,
            "error": f"No credit row for {ticker}",
        }
    row = hits.iloc[0]
    industry = str(row.get("industry_group") or "")
    meds = peer_medians(df, industry) if industry else {}
    peer_kpi = {
        k: {"label": kpi_label(k), "value": _json_num(meds.get(k))}
        for k in kpi_keys
        if k in meds or k in row.index
    }
    # Only include medians that exist
    peer_kpi = {
        k: v
        for k, v in peer_kpi.items()
        if k in meds
    }

    block: dict[str, Any] = {
        "role": role,
        "ticker": str(row["ticker"]),
        "found": True,
        "company": row.get("company") or ticker,
        "sector": row.get("sector") or "",
        "industry_group": industry,
        "cohort": row.get("cohort") or "",
        "period": row.get("period") or "",
        "has_financials": bool(row.get("has_financials")),
        "peer_benchmark": bool(row.get("peer_benchmark")),
        "kpis": _pick_kpis(row, kpi_keys),
        "peer_medians": peer_kpi,
    }

    if include_signals:
        scan = scan_qualitative_signals(ticker)
        block["signals"] = {
            "qualitative_penalty": scan.get("qualitative_penalty"),
            "matched_keywords": scan.get("matched_keywords") or [],
            "hit_count": len(scan.get("signal_hits") or []),
            "summary": [
                {
                    "source": h.get("source"),
                    "date": h.get("date"),
                    "title": h.get("title"),
                    "keywords": h.get("keywords"),
                }
                for h in (scan.get("signal_hits") or [])[:8]
            ],
        }
    return block


def _industry_medians(sub: pd.DataFrame, kpi_keys: list[str]) -> dict[str, float]:
    """Median of selected KPI columns for an industry subset."""
    out: dict[str, float] = {}
    for c in kpi_keys:
        if c not in sub.columns:
            continue
        val = pd.to_numeric(sub[c], errors="coerce").median()
        if pd.notna(val):
            out[c] = float(val)
    return out


def _industry_block(
    df: pd.DataFrame,
    industry: str,
    kpi_keys: list[str],
    *,
    primary_score: str,
    role: str,
) -> dict[str, Any]:
    sub = df[df["industry_group"].astype(str).str.lower() == industry.lower()].copy()
    if sub.empty:
        return {
            "role": role,
            "industry_group": industry,
            "found": False,
            "error": f"No companies for industry {industry}",
        }
    scored = sub[sub["has_financials"]].copy()
    # Prefer cohort peer_medians for credit ratios; fill remaining selected KPIs from frame
    meds = peer_medians(df, industry)
    frame_meds = _industry_medians(scored if not scored.empty else sub, kpi_keys)
    for k, v in frame_meds.items():
        meds.setdefault(k, v)

    score_col = primary_score if primary_score in scored.columns else "credit_score"
    scores = pd.to_numeric(scored.get(score_col), errors="coerce").dropna()

    ranked = scored.dropna(subset=[score_col] if score_col in scored.columns else []).copy()
    if score_col in ranked.columns:
        ranked = ranked.sort_values(score_col, ascending=False, na_position="last")

    members = []
    for _, r in ranked.iterrows():
        members.append(
            {
                "ticker": r["ticker"],
                "company": r.get("company"),
                "kpis": _pick_kpis(r, kpi_keys),
                "primary_score": _json_num(r.get(score_col)),
            }
        )

    distribution: dict[str, Any] = {
        "metric": score_col,
        "count": int(len(scores)),
    }
    if not scores.empty:
        distribution.update(
            {
                "min": _json_num(scores.min()),
                "median": _json_num(scores.median()),
                "max": _json_num(scores.max()),
                "mean": _json_num(scores.mean()),
            }
        )

    return {
        "role": role,
        "industry_group": industry,
        "found": True,
        "cohort": str(scored["cohort"].iloc[0]) if not scored.empty else "",
        "member_count": int(len(sub)),
        "with_financials": int(len(scored)),
        "peer_medians": {
            k: {"label": kpi_label(k), "value": _json_num(v)}
            for k, v in meds.items()
            if not kpi_keys or k in kpi_keys
        },
        "score_distribution": distribution,
        "ranked_members": members,
        "top": members[:5],
        "bottom": list(reversed(members[-5:])) if members else [],
    }


def _chart_specs(context: dict[str, Any], spec: ReportSpec) -> list[dict[str, Any]]:
    """Lightweight chart hints for the LLM / HTML scaffold."""
    charts: list[dict[str, Any]] = []
    primary = PRIMARY_SCORE_BY_MODE[spec.mode]

    for ind in context.get("industries") or []:
        if not ind.get("found"):
            continue
        members = ind.get("ranked_members") or []
        if not members:
            continue
        charts.append(
            {
                "id": f"bar_{ind['industry_group'].replace(' ', '_').lower()}",
                "type": "bar",
                "title": f"{ind['industry_group']} — {kpi_label(primary)}",
                "x": [m["ticker"] for m in members],
                "y": [m.get("primary_score") for m in members],
            }
        )

    # Company vs peer median for first subject company
    for co in context.get("companies") or []:
        if co.get("role") != "subject" or not co.get("found"):
            continue
        labels = []
        company_vals = []
        peer_vals = []
        for k, cell in (co.get("kpis") or {}).items():
            peer = (co.get("peer_medians") or {}).get(k)
            if peer is None:
                continue
            labels.append(cell.get("label") or k)
            company_vals.append(cell.get("value"))
            peer_vals.append(peer.get("value"))
        if labels:
            charts.append(
                {
                    "id": f"compare_{co['ticker'].lower()}",
                    "type": "grouped_bar",
                    "title": f"{co['ticker']} vs peer median",
                    "categories": labels,
                    "series": [
                        {"name": co["ticker"], "values": company_vals},
                        {"name": "Peer median", "values": peer_vals},
                    ],
                }
            )
        break
    return charts


def assemble_context(
    spec: ReportSpec,
    *,
    credit_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Build JSON-serializable ReportContext from a validated ReportSpec."""
    kpi_keys = spec.resolved_kpis()
    primary = PRIMARY_SCORE_BY_MODE[spec.mode]
    df = credit_df if credit_df is not None else build_credit_table(
        include_signals=spec.include_signals
    )

    companies: list[dict[str, Any]] = []
    for t in spec.subjects.companies:
        companies.append(
            _company_block(
                df, t, kpi_keys, include_signals=spec.include_signals, role="subject"
            )
        )
    for t in spec.comparatives.companies:
        companies.append(
            _company_block(
                df, t, kpi_keys, include_signals=spec.include_signals, role="comparative"
            )
        )

    industries: list[dict[str, Any]] = []
    for ind in spec.subjects.industries:
        industries.append(
            _industry_block(df, ind, kpi_keys, primary_score=primary, role="subject")
        )
    for ind in spec.comparatives.industries:
        industries.append(
            _industry_block(
                df, ind, kpi_keys, primary_score=primary, role="comparative"
            )
        )

    context: dict[str, Any] = {
        "title": spec.default_title(),
        "mode": spec.mode,
        "language": spec.language,
        "include_signals": spec.include_signals,
        "selected_kpis": [
            {"key": k, "label": kpi_label(k)} for k in kpi_keys
        ],
        "subjects": {
            "companies": list(spec.subjects.companies),
            "industries": list(spec.subjects.industries),
        },
        "comparatives": {
            "companies": list(spec.comparatives.companies),
            "industries": list(spec.comparatives.industries),
        },
        "companies": companies,
        "industries": industries,
        "disclaimer": (
            "Research-grade analysis from local CVM financials and optional "
            "notice/transcript keyword signals. Not a bureau credit rating or "
            "investment recommendation."
        ),
    }
    context["chart_specs"] = _chart_specs(context, spec)
    return context
