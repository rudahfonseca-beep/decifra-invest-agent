"""Assemble APV inputs from local CVM history + market data for a ticker (IMP-036)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from decifra.credit.metrics import extract_kpis
from decifra.valuation.apv import APVResult, compute_apv
from decifra.valuation.assumptions import build_default_assumptions
from decifra.valuation.dcf import _CVM_THOUSANDS_SCALE, compute_wacc, project_fcff
from decifra.valuation.historical import build_annual_history
from decifra.valuation.market_data import fetch_market_data


def assemble_apv(ticker: str, *, peers: list[str] | None = None) -> dict[str, Any]:
    """Build unlevered FCFF + interest path from lake, run APV, compare to market.

    Returns a dict with ``apv`` (APVResult fields), ``apv_discount_pct``
    ((V_L - market_cap) / market_cap), inputs, warnings, and lineage.
    """
    warnings: list[str] = []
    hist = build_annual_history(ticker)
    kpis = extract_kpis(ticker)
    market = fetch_market_data(ticker)
    assumptions, _ = build_default_assumptions(ticker, peers=peers)

    base_revenue: float | None = None
    if not hist.empty and pd.notna(hist["revenue"].iloc[-1]):
        base_revenue = float(hist["revenue"].iloc[-1])
    elif kpis.get("revenue") is not None:
        base_revenue = float(kpis["revenue"]) * _CVM_THOUSANDS_SCALE
    if not base_revenue or base_revenue <= 0:
        warnings.append("No revenue base; FCFF path may be zero.")
        base_revenue = 0.0

    rows = project_fcff(assumptions, base_revenue)
    fcff_path = [float(r["fcff"]) for r in rows]

    interest_level = 0.0
    if not hist.empty and "interest_expense" in hist.columns and pd.notna(hist["interest_expense"].iloc[-1]):
        interest_level = abs(float(hist["interest_expense"].iloc[-1]))
    elif kpis.get("interest_expense") is not None:
        interest_level = abs(float(kpis["interest_expense"])) * _CVM_THOUSANDS_SCALE
    elif kpis.get("financial_result") is not None and float(kpis["financial_result"]) < 0:
        interest_level = abs(float(kpis["financial_result"])) * _CVM_THOUSANDS_SCALE
    else:
        warnings.append("Interest path unavailable; tax shields set to 0.")

    interest_path = [interest_level] * len(fcff_path)

    gross_debt = None
    if not hist.empty and pd.notna(hist["gross_debt"].iloc[-1]):
        gross_debt = float(hist["gross_debt"].iloc[-1])
    elif kpis.get("gross_debt") is not None:
        gross_debt = float(kpis["gross_debt"]) * _CVM_THOUSANDS_SCALE

    market_cap = market.get("market_cap")
    if market_cap is None and market.get("price") and market.get("shares_outstanding"):
        market_cap = float(market["price"]) * float(market["shares_outstanding"])

    wacc_info = compute_wacc(assumptions, market_cap=market_cap, gross_debt=gross_debt)
    # Research proxy for unlevered cost of capital: cost of equity (APV ku).
    ku = float(wacc_info["cost_of_equity"])

    apv: APVResult = compute_apv(
        unlevered_fcff=fcff_path,
        unlevered_cost_of_capital=ku,
        debt_interest=interest_path,
        tax_rate=float(assumptions.tax_rate),
        distress_cost_pv=0.0,
        terminal_growth=float(assumptions.terminal_growth),
    )

    discount_pct: float | None = None
    if market_cap and market_cap > 0:
        discount_pct = (apv.v_l - float(market_cap)) / float(market_cap)
    else:
        warnings.append("Market cap unavailable; cannot compute APV discount vs market.")

    return {
        "ticker": ticker.upper(),
        "apv": apv.to_dict(),
        "apv_discount_pct": discount_pct,
        "ku": ku,
        "market_cap": market_cap,
        "fcff_path": fcff_path,
        "interest_path": interest_path,
        "warnings": warnings,
        "lineage": {
            "source_doc": "CVM_DFP_ITR+market",
            "freshness": "ITR/DFP lake + market cache",
        },
    }
