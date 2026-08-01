"""JSON serializers for Streamlit-parity research endpoints (credit / valuation / report)."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from decifra.assistant.retrieve import coverage_status
from decifra.credit.scoring import (
    FINANCIAL_RATIOS,
    NON_FINANCIAL_RATIOS,
    build_credit_table,
    peer_medians,
)
from decifra.credit.signals import scan_qualitative_signals
from decifra.http_util import normalize_ticker
from decifra.report.catalog import ALL_KPIS, KPI_LABELS, PCT_KPIS, default_kpis, kpi_label
from decifra.report.generate import build_report_artifacts
from decifra.report.spec import EntitySelection, ReportSpec, SpecValidationError, validate_spec
from decifra.valuation.assumptions import DcfAssumptions, build_default_assumptions
from decifra.valuation.dcf import discount_cash_flow, sensitivity_grid
from decifra.valuation.multiples import MULTIPLE_LABELS, relative_valuation


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (pd.Timestamp,)):
        return str(v)
    if hasattr(v, "item"):
        try:
            return _jsonable(v.item())
        except Exception:
            pass
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    return v


def _df_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rec = {k: _jsonable(row.get(k)) for k in df.columns}
        out.append(rec)
    return out


_CREDIT_CACHE: dict[str, Any] = {"key": None, "df": None}


def get_credit_df(*, include_signals: bool = True, refresh: bool = False) -> pd.DataFrame:
    key = f"sig={include_signals}"
    if not refresh and _CREDIT_CACHE.get("key") == key and _CREDIT_CACHE.get("df") is not None:
        return _CREDIT_CACHE["df"]
    df = build_credit_table(include_signals=include_signals)
    _CREDIT_CACHE["key"] = key
    _CREDIT_CACHE["df"] = df
    return df


DISPLAY_COLS = [
    "ticker",
    "company",
    "cnpj",
    "isins",
    "industry_group",
    "sector",
    "cohort",
    "period",
    "has_financials",
    "credit_score",
    "fundamental_score",
    "qualitative_penalty",
    "debt_to_equity",
    "current_ratio",
    "interest_coverage",
    "net_margin",
    "equity_to_assets",
    "roe",
    "peer_benchmark",
    "signal_hits",
]


def credit_table_payload(
    *,
    industry: str | None = None,
    cohort: str | None = None,
    include_signals: bool = True,
    show_incomplete: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    df = get_credit_df(include_signals=include_signals, refresh=refresh)
    view = df if show_incomplete else df[df["has_financials"]].copy()
    industries = sorted(view["industry_group"].dropna().unique().tolist())
    cohorts = sorted(view["cohort"].dropna().unique().tolist())
    if industry and industry != "All":
        view = view[view["industry_group"] == industry]
    if cohort and cohort != "All":
        view = view[view["cohort"] == cohort]

    cols = [c for c in DISPLAY_COLS if c in view.columns]
    rows = _df_records(view[cols] if cols else view)
    meds = peer_medians(df, industry) if industry and industry != "All" else {}
    scored = view["credit_score"].dropna() if "credit_score" in view.columns else pd.Series(dtype=float)
    return {
        "industries": ["All"] + industries,
        "cohorts": ["All"] + cohorts,
        "filters": {
            "industry": industry or "All",
            "cohort": cohort or "All",
            "include_signals": include_signals,
            "show_incomplete": show_incomplete,
        },
        "summary": {
            "companies": int(len(view)),
            "median_credit_score": _jsonable(float(scored.median())) if len(scored) else None,
            "mean_credit_score": _jsonable(float(scored.mean())) if len(scored) else None,
            "with_peer_benchmark": int(view["peer_benchmark"].fillna(False).sum())
            if "peer_benchmark" in view.columns
            else 0,
        },
        "peer_medians": {k: _jsonable(v) for k, v in meds.items()},
        "peer_median_labels": {k: KPI_LABELS.get(k, k) for k in meds},
        "pct_kpis": list(PCT_KPIS),
        "rows": rows,
    }


def industries_payload(*, include_signals: bool = True) -> dict[str, Any]:
    df = get_credit_df(include_signals=include_signals)
    view = df[df["has_financials"]].copy() if "has_financials" in df.columns else df
    items: list[dict[str, Any]] = []
    for group, gdf in view.groupby("industry_group", sort=True):
        scored = gdf["credit_score"].dropna()
        items.append(
            {
                "industry_group": group,
                "cohort": gdf["cohort"].iloc[0] if "cohort" in gdf.columns else None,
                "companies": int(len(gdf)),
                "median_credit_score": _jsonable(float(scored.median())) if len(scored) else None,
                "mean_credit_score": _jsonable(float(scored.mean())) if len(scored) else None,
                "tickers": sorted(gdf["ticker"].astype(str).tolist()),
            }
        )
    return {"industries": items}


def tickers_payload(
    *,
    industry: str | None = None,
    include_signals: bool = True,
    show_incomplete: bool = True,
) -> dict[str, Any]:
    df = get_credit_df(include_signals=include_signals)
    view = df if show_incomplete else df[df["has_financials"]].copy()
    if industry and industry != "All":
        view = view[view["industry_group"] == industry]
    cols = [
        c
        for c in (
            "ticker",
            "company",
            "cnpj",
            "isins",
            "industry_group",
            "sector",
            "cohort",
            "period",
            "has_financials",
            "credit_score",
            "peer_benchmark",
        )
        if c in view.columns
    ]
    rows = _df_records(view[cols].sort_values(["industry_group", "ticker"]))
    return {"tickers": rows, "count": len(rows)}


def credit_detail_payload(ticker: str, *, include_signals: bool = True) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    # Never rebuild the universe-wide signal scan for one ticker (was causing
    # multi-minute requests / Vite proxy 500s). Use fundamental table, then
    # scan notices/transcripts for this ticker only.
    df = get_credit_df(include_signals=False)
    hits = df[df["ticker"].astype(str).str.upper() == t]
    if hits.empty:
        return {"found": False, "ticker": t, "error": "unknown ticker"}
    row = hits.iloc[0]
    cohort = row.get("cohort") or "non_financial"
    ratio_dirs = FINANCIAL_RATIOS if cohort == "financial" else NON_FINANCIAL_RATIOS
    meds = peer_medians(df, str(row.get("industry_group") or ""))
    ratios = []
    for col, hib in ratio_dirs.items():
        ratios.append(
            {
                "key": col,
                "label": KPI_LABELS.get(col, col),
                "company": _jsonable(row.get(col)),
                "peer_median": _jsonable(meds.get(col)),
                "higher_better": bool(hib),
                "pct": col in PCT_KPIS,
            }
        )
    signals = None
    qual_penalty = _jsonable(row.get("qualitative_penalty"))
    credit_score = _jsonable(row.get("credit_score"))
    fund = row.get("fundamental_score")
    if include_signals:
        raw = scan_qualitative_signals(t)
        # Normalize hits for JSON (keywords lists, paths as str)
        hits_out = []
        for h in raw.get("signal_hits") or []:
            hits_out.append(
                {
                    "source": h.get("source"),
                    "date": str(h.get("date") or ""),
                    "title": h.get("title"),
                    "keywords": list(h.get("keywords") or []),
                    "path": str(h.get("path") or ""),
                    "url": h.get("url") or "",
                }
            )
        qual_penalty = _jsonable(raw.get("qualitative_penalty"))
        if fund is not None and qual_penalty is not None:
            credit_score = _jsonable(float(fund) - float(qual_penalty))
        signals = {
            "ticker": t,
            "qualitative_penalty": qual_penalty,
            "matched_keywords": list(raw.get("matched_keywords") or []),
            "signal_hits": hits_out,
        }
    return {
        "found": True,
        "ticker": t,
        "company": row.get("company"),
        "industry_group": row.get("industry_group"),
        "sector": row.get("sector"),
        "cohort": cohort,
        "period": row.get("period"),
        "cnpj": row.get("cnpj"),
        "isins": list(row.get("isins") or []) if not isinstance(row.get("isins"), float) else [],
        "credit_score": credit_score,
        "fundamental_score": _jsonable(fund),
        "qualitative_penalty": qual_penalty,
        "peer_benchmark": bool(row.get("peer_benchmark")),
        "has_financials": bool(row.get("has_financials")),
        "ratios": ratios,
        "signals": signals,
    }


def coverage_payload() -> dict[str, Any]:
    rows = coverage_status()
    missing = [
        r
        for r in rows
        if not r.get("income_statement") or not r.get("balance_sheet")
    ]
    return {"rows": rows, "missing_financials": len(missing)}


def valuation_defaults_payload(ticker: str, peers: list[str] | None = None) -> dict[str, Any]:
    from decifra.store.folders import list_tickers

    t = normalize_ticker(ticker)
    peer_list = [normalize_ticker(p) for p in (peers or [])]
    defaults, notes = build_default_assumptions(t, peers=peer_list or None)
    # Prefer cached fundamental credit table (no universe-wide signal scan).
    df = get_credit_df(include_signals=False)
    row = df[df["ticker"] == t]
    default_group = row.iloc[0]["industry_group"] if not row.empty else None
    default_peers = (
        df[(df["industry_group"] == default_group) & (df["ticker"] != t)]["ticker"].tolist()
        if default_group
        else []
    )
    all_tickers = (
        sorted(df["ticker"].dropna().astype(str).unique().tolist())
        if not df.empty
        else list_tickers()
    )
    return {
        "ticker": t,
        "default_peers": default_peers[:8],
        "assumptions": defaults.to_dict(),
        "notes": [n.to_dict() for n in notes],
        "all_tickers": all_tickers,
    }


def valuation_run_payload(
    ticker: str,
    *,
    peers: list[str] | None = None,
    assumptions: dict[str, Any] | None = None,
    multiples_stat: str = "median",
    include_sensitivity: bool = True,
) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    peer_list = [normalize_ticker(p) for p in (peers or [])]
    if assumptions:
        base, _ = build_default_assumptions(t, peers=peer_list or None)
        fields = {f: getattr(base, f) for f in DcfAssumptions.__dataclass_fields__}
        fields.update({k: assumptions[k] for k in assumptions if k in fields})
        assump = DcfAssumptions(**fields)
    else:
        assump, _ = build_default_assumptions(t, peers=peer_list or None)

    dcf = discount_cash_flow(t, assump, peers=peer_list or None)
    grid = sensitivity_grid(t, assump) if include_sensitivity else None
    multiples = None
    if peer_list:
        multiples = relative_valuation(t, peer_list, stat=multiples_stat).to_dict()
    return {
        "ticker": t,
        "peers": peer_list,
        "assumptions": assump.to_dict(),
        "dcf": dcf.to_dict(),
        "sensitivity": grid,
        "multiples": multiples,
        "multiple_labels": MULTIPLE_LABELS,
        "extreme_upside": bool(
            dcf.upside_pct is not None and abs(float(dcf.upside_pct)) > 1.0
        ),
    }


def report_catalog_payload() -> dict[str, Any]:
    from decifra.store.folders import list_tickers

    df = get_credit_df(include_signals=False)
    tickers = (
        sorted(df["ticker"].dropna().astype(str).unique().tolist())
        if not df.empty
        else list_tickers()
    )
    industries = (
        sorted(df["industry_group"].dropna().astype(str).unique().tolist())
        if not df.empty and "industry_group" in df.columns
        else []
    )
    return {
        "modes": ["credit", "equity"],
        "languages": ["pt", "en"],
        "kpis": [{"key": k, "label": kpi_label(k)} for k in ALL_KPIS],
        "default_kpis": {"credit": default_kpis("credit"), "equity": default_kpis("equity")},
        "tickers": tickers,
        "industries": industries,
    }


def report_build_payload(body: dict[str, Any]) -> dict[str, Any]:
    df = get_credit_df(include_signals=bool(body.get("include_signals", True)))
    all_tickers = sorted(df["ticker"].dropna().unique().tolist())
    all_industries = sorted(df["industry_group"].dropna().unique().tolist())
    mode = body.get("mode") or "credit"
    try:
        spec = validate_spec(
            ReportSpec(
                mode=mode,
                title=body.get("title") or "",
                subjects=EntitySelection(
                    companies=list(body.get("subject_companies") or []),
                    industries=list(body.get("subject_industries") or []),
                ),
                comparatives=EntitySelection(
                    companies=list(body.get("compare_companies") or []),
                    industries=list(body.get("compare_industries") or []),
                ),
                kpis=list(body.get("kpis") or default_kpis(mode)),
                include_signals=bool(body.get("include_signals", True)),
                language=body.get("language") or "pt",
            ),
            known_tickers=all_tickers,
            known_industries=all_industries,
        )
    except SpecValidationError as exc:
        return {"ok": False, "error": str(exc)}

    result = build_report_artifacts(
        spec,
        generate=bool(body.get("generate")),
        credit_df=df,
    )
    return {
        "ok": True,
        "dir": str(result.get("dir") or ""),
        "prompt_markdown": result.get("prompt_markdown"),
        "context": result.get("context"),
        "generated": result.get("generated"),
        "generate_error": result.get("generate_error"),
        "html_path": str(result["html_path"]) if result.get("html_path") else None,
    }
