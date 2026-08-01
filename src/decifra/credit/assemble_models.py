"""Assemble Merton / capacity inputs from CVM KPIs + market data (IMP-036)."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from decifra.config import RISK_FREE_RATE_DEFAULT
from decifra.credit.capacity import CapacityResult, evaluate_capacity
from decifra.credit.merton import MertonResult, merton_dtd
from decifra.credit.metrics import extract_kpis
from decifra.store.folders import company_dir
from decifra.valuation.dcf import _CVM_THOUSANDS_SCALE
from decifra.valuation.historical import build_annual_history
from decifra.valuation.market_data import fetch_market_data

DEFAULT_ASSET_VOL = 0.25
DEFAULT_HORIZON_YEARS = 1.0


def _equity_vol_annualized(ticker: str) -> float | None:
    """Annualized equity vol from weekly returns in local prices.csv."""
    path = company_dir(ticker) / "financials" / "prices.csv"
    if not path.exists():
        return None
    try:
        px = pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return None
    if px.empty:
        return None
    date_col = "date" if "date" in px.columns else None
    close_col = (
        "close"
        if "close" in px.columns
        else ("adjustedClose" if "adjustedClose" in px.columns else None)
    )
    if date_col is None or close_col is None:
        return None
    if pd.api.types.is_numeric_dtype(px[date_col]):
        px["_date"] = pd.to_datetime(px[date_col], unit="s", utc=True, errors="coerce")
    else:
        px["_date"] = pd.to_datetime(px[date_col], utc=True, errors="coerce")
    px = px.dropna(subset=["_date"]).sort_values("_date")
    if px.empty:
        return None
    weekly = px.set_index("_date")[close_col].resample("W-FRI").last().dropna().pct_change().dropna()
    if len(weekly) < 26:
        return None
    return float(weekly.std() * math.sqrt(52))


def _scale_kpi_money(kpis: dict[str, Any], key: str) -> float | None:
    v = kpis.get(key)
    if v is None:
        return None
    return float(v) * _CVM_THOUSANDS_SCALE


def assemble_capacity(ticker: str) -> dict[str, Any]:
    """ND/EBITDA + DSCR capacity flags from latest DFP KPIs."""
    kpis = extract_kpis(ticker)
    hist = build_annual_history(ticker)

    net_debt = None
    if not hist.empty and pd.notna(hist["net_debt"].iloc[-1]):
        net_debt = float(hist["net_debt"].iloc[-1])
    else:
        net_debt = _scale_kpi_money(kpis, "net_debt")

    ebit = None
    if not hist.empty and pd.notna(hist["ebit"].iloc[-1]):
        ebit = float(hist["ebit"].iloc[-1])
    else:
        ebit = _scale_kpi_money(kpis, "ebit")

    # Research proxy: EBITDA ≈ EBIT (D&A often incomplete in KPI extract).
    ebitda = ebit

    ocf = None
    if not hist.empty and "operating_cf" in hist.columns and pd.notna(hist["operating_cf"].iloc[-1]):
        ocf = float(hist["operating_cf"].iloc[-1])
    else:
        ocf = _scale_kpi_money(kpis, "operating_cf")
    if ocf is None:
        ocf = ebitda

    interest = None
    if not hist.empty and "interest_expense" in hist.columns and pd.notna(hist["interest_expense"].iloc[-1]):
        interest = abs(float(hist["interest_expense"].iloc[-1]))
    else:
        ie = kpis.get("interest_expense")
        if ie is not None:
            interest = abs(float(ie)) * _CVM_THOUSANDS_SCALE
        elif kpis.get("financial_result") is not None and float(kpis["financial_result"]) < 0:
            interest = abs(float(kpis["financial_result"])) * _CVM_THOUSANDS_SCALE

    # Mandatory amort proxy: 10% of short-term debt when available.
    debt_st = _scale_kpi_money(kpis, "debt_st") or 0.0
    amort = 0.1 * debt_st if debt_st else 0.0
    debt_service = (interest or 0.0) + amort
    if debt_service <= 0:
        debt_service = None

    result: CapacityResult = evaluate_capacity(
        net_debt=net_debt,
        ebitda=ebitda,
        ocf_or_ebitda_proxy=ocf,
        debt_service=debt_service,
        lineage={"source_doc": "CVM_DFP_ITR", "freshness": kpis.get("period") or "lake"},
    )
    return {
        "ticker": ticker.upper(),
        "capacity": result.to_dict(),
        "inputs": {
            "net_debt": net_debt,
            "ebitda": ebitda,
            "ocf": ocf,
            "debt_service": debt_service,
        },
        "lineage": {"source_doc": "CVM_DFP_ITR", "period": kpis.get("period")},
    }


def assemble_merton(
    ticker: str,
    *,
    risk_free: float | None = None,
    horizon_years: float = DEFAULT_HORIZON_YEARS,
    asset_vol: float | None = None,
) -> dict[str, Any]:
    """Merton DtD/PD from market cap + book debt and equity-vol → asset-vol proxy."""
    warnings: list[str] = []
    kpis = extract_kpis(ticker)
    hist = build_annual_history(ticker)
    market = fetch_market_data(ticker)

    market_cap = market.get("market_cap")
    if market_cap is None and market.get("price") and market.get("shares_outstanding"):
        market_cap = float(market["price"]) * float(market["shares_outstanding"])

    gross_debt = None
    if not hist.empty and pd.notna(hist["gross_debt"].iloc[-1]):
        gross_debt = float(hist["gross_debt"].iloc[-1])
    else:
        gross_debt = _scale_kpi_money(kpis, "gross_debt")

    net_debt = None
    if not hist.empty and pd.notna(hist["net_debt"].iloc[-1]):
        net_debt = float(hist["net_debt"].iloc[-1])
    else:
        net_debt = _scale_kpi_money(kpis, "net_debt")

    if market_cap is None or market_cap <= 0:
        warnings.append("Market cap missing; Merton skipped.")
        return {
            "ticker": ticker.upper(),
            "merton": None,
            "warnings": warnings,
            "lineage": {"source_doc": "market+CVM"},
        }
    if gross_debt is None or gross_debt <= 0:
        warnings.append("Gross debt missing/zero; Merton skipped.")
        return {
            "ticker": ticker.upper(),
            "merton": None,
            "warnings": warnings,
            "lineage": {"source_doc": "market+CVM"},
        }

    # Asset value proxy: equity market value + net debt (floor at equity + gross).
    nd = net_debt if net_debt is not None else gross_debt
    asset_value = float(market_cap) + max(float(nd), 0.0)
    debt_face = float(gross_debt)

    sigma_e = _equity_vol_annualized(ticker)
    if asset_vol is not None:
        sigma_v = asset_vol
    elif sigma_e and asset_value > 0:
        e_over_v = float(market_cap) / asset_value
        sigma_v = max(0.05, min(1.5, sigma_e * e_over_v))
        warnings.append(f"Asset vol ≈ equity_vol * E/V = {sigma_e:.2%} * {e_over_v:.2f} → {sigma_v:.2%}")
    else:
        sigma_v = DEFAULT_ASSET_VOL
        warnings.append(f"Using default asset vol {DEFAULT_ASSET_VOL:.0%}")

    rf = RISK_FREE_RATE_DEFAULT if risk_free is None else risk_free
    result: MertonResult = merton_dtd(
        asset_value=asset_value,
        debt_face=debt_face,
        risk_free=rf,
        horizon_years=horizon_years,
        asset_vol=sigma_v,
    )
    return {
        "ticker": ticker.upper(),
        "merton": result.to_dict(),
        "inputs": {
            "asset_value": asset_value,
            "debt_face": debt_face,
            "risk_free": rf,
            "horizon_years": horizon_years,
            "asset_vol": sigma_v,
            "equity_vol": sigma_e,
        },
        "warnings": warnings,
        "lineage": {"source_doc": "market+CVM", "freshness": "prices.csv + DFP/ITR"},
    }
