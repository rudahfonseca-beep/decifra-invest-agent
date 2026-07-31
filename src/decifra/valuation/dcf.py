"""FCFF projection and WACC discounting: enterprise value -> equity value -> per share.

For each forecast year t = 1..N:

    revenue_t   = revenue_{t-1} * (1 + growth_t)         growth fades linearly from
                                                          `revenue_growth_y1` to `terminal_growth`
    ebit_t      = revenue_t * ebit_margin                 (flat across the horizon)
    nopat_t     = ebit_t * (1 - tax_rate)
    da_t        = revenue_t * da_pct_revenue
    capex_t     = revenue_t * capex_pct_revenue           (terminal year: capex_t = da_t, i.e.
                                                            steady-state reinvestment)
    nwc_inv_t   = nwc_pct_revenue * (revenue_t - revenue_{t-1})
    fcff_t      = nopat_t + da_t - capex_t - nwc_inv_t

WACC = E/(E+D) * cost_of_equity + D/(E+D) * cost_of_debt * (1 - tax_rate), where
cost_of_equity = risk_free_rate + beta * equity_risk_premium + country_risk_premium
(CAPM), E = market cap, D = book gross debt. `assumptions.wacc_override` bypasses
this entirely when the user wants to type a WACC directly.

Terminal value (Gordon growth): TV_N = fcff_N * (1 + g) / (WACC - g), discounted
back N years. Enterprise value = sum(PV(fcff_t)) + PV(TV_N). Equity value =
EV - net debt. Per-share value = equity value / shares outstanding.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

import pandas as pd

from decifra.credit.metrics import extract_kpis
from decifra.valuation.assumptions import DcfAssumptions, build_default_assumptions
from decifra.valuation.historical import build_annual_history
from decifra.valuation.market_data import fetch_market_data

_TERMINAL_GROWTH_BUFFER = 0.005


def _fade(y1: float, terminal: float, n: int) -> list[float]:
    """Linearly fade growth from year 1 (`y1`) to the final year (`terminal`), inclusive."""
    if n <= 1:
        return [terminal]
    return [y1 + (terminal - y1) * i / (n - 1) for i in range(n)]


def compute_cost_of_equity(a: DcfAssumptions) -> float:
    """CAPM: Rf + beta * ERP + country risk premium."""
    return a.risk_free_rate + a.beta * a.equity_risk_premium + a.country_risk_premium


def compute_wacc(
    a: DcfAssumptions, *, market_cap: float | None, gross_debt: float | None
) -> dict[str, Any]:
    """Weighted-average cost of capital; `a.wacc_override` bypasses CAPM + weights entirely."""
    cost_of_equity = compute_cost_of_equity(a)
    after_tax_kd = a.cost_of_debt * (1 - a.tax_rate)

    if a.wacc_override is not None:
        return {
            "wacc": a.wacc_override,
            "cost_of_equity": cost_of_equity,
            "after_tax_cost_of_debt": after_tax_kd,
            "equity_weight": None,
            "debt_weight": None,
            "source": "user override",
        }

    e = market_cap or 0.0
    d = gross_debt or 0.0
    if e + d <= 0:
        return {
            "wacc": cost_of_equity,
            "cost_of_equity": cost_of_equity,
            "after_tax_cost_of_debt": after_tax_kd,
            "equity_weight": 1.0,
            "debt_weight": 0.0,
            "source": "cost of equity only (no market cap/debt data)",
        }
    ew = e / (e + d)
    dw = d / (e + d)
    return {
        "wacc": ew * cost_of_equity + dw * after_tax_kd,
        "cost_of_equity": cost_of_equity,
        "after_tax_cost_of_debt": after_tax_kd,
        "equity_weight": ew,
        "debt_weight": dw,
        "source": "CAPM cost of equity + market-value weights",
    }


def project_fcff(a: DcfAssumptions, base_revenue: float) -> list[dict[str, Any]]:
    """Year-by-year FCFF projection (undiscounted) from `base_revenue`."""
    growth_path = _fade(a.revenue_growth_y1, a.terminal_growth, a.forecast_years)
    rows: list[dict[str, Any]] = []
    prev_revenue = base_revenue
    for i, g in enumerate(growth_path, start=1):
        revenue = prev_revenue * (1 + g)
        ebit = revenue * a.ebit_margin
        nopat = ebit * (1 - a.tax_rate)
        da = revenue * a.da_pct_revenue
        is_terminal_year = i == a.forecast_years
        capex = da if is_terminal_year else revenue * a.capex_pct_revenue
        nwc_investment = a.nwc_pct_revenue * (revenue - prev_revenue)
        fcff = nopat + da - capex - nwc_investment
        rows.append(
            {
                "year": i,
                "growth": g,
                "revenue": revenue,
                "ebit": ebit,
                "nopat": nopat,
                "da": da,
                "capex": capex,
                "nwc_investment": nwc_investment,
                "fcff": fcff,
            }
        )
        prev_revenue = revenue
    return rows


@dataclass
class YearProjection:
    year: int
    growth: float
    revenue: float
    ebit: float
    nopat: float
    da: float
    capex: float
    nwc_investment: float
    fcff: float
    discount_factor: float
    pv_fcff: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DcfResult:
    ticker: str
    assumptions: DcfAssumptions
    base_revenue: float
    years: list[YearProjection]
    cost_of_equity: float
    after_tax_cost_of_debt: float
    equity_weight: float | None
    debt_weight: float | None
    wacc: float
    wacc_source: str
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    net_debt: float | None
    equity_value: float | None
    shares_outstanding: float | None
    value_per_share: float | None
    current_price: float | None
    upside_pct: float | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            **{k: v for k, v in asdict(self).items() if k not in {"assumptions", "years"}},
            "assumptions": self.assumptions.to_dict(),
            "years": [y.to_dict() for y in self.years],
        }


def discount_cash_flow(
    ticker: str,
    assumptions: DcfAssumptions | None = None,
    *,
    peers: list[str] | None = None,
    _hist: pd.DataFrame | None = None,
    _kpis: dict[str, Any] | None = None,
    _market: dict[str, Any] | None = None,
) -> DcfResult:
    """Run the full FCFF/WACC DCF for `ticker`.

    `_hist`/`_kpis`/`_market` are internal hooks so `sensitivity_grid()` can
    reuse one fetch across many assumption variants instead of re-reading the
    local CSVs and re-hitting the market-data cache for every grid cell.
    """
    warnings: list[str] = []
    hist = _hist if _hist is not None else build_annual_history(ticker)
    kpis = _kpis if _kpis is not None else extract_kpis(ticker)
    market = _market if _market is not None else fetch_market_data(ticker)

    if assumptions is None:
        assumptions, _ = build_default_assumptions(ticker, peers=peers)

    base_revenue: float | None = None
    if not hist.empty and pd.notna(hist["revenue"].iloc[-1]):
        base_revenue = float(hist["revenue"].iloc[-1])
    elif kpis.get("revenue") is not None:
        base_revenue = float(kpis["revenue"])
    if not base_revenue or base_revenue <= 0:
        warnings.append("No usable revenue base found locally; projection starts from 0.")
        base_revenue = 0.0

    gross_debt = kpis.get("gross_debt")
    if gross_debt is None and not hist.empty and pd.notna(hist["gross_debt"].iloc[-1]):
        gross_debt = float(hist["gross_debt"].iloc[-1])

    net_debt = kpis.get("net_debt")
    if net_debt is None and not hist.empty and pd.notna(hist["net_debt"].iloc[-1]):
        net_debt = float(hist["net_debt"].iloc[-1])
    if net_debt is None:
        warnings.append("Net debt unavailable locally; showing enterprise value only.")

    market_cap = market.get("market_cap")
    if market_cap is None and market.get("price") and market.get("shares_outstanding"):
        market_cap = market["price"] * market["shares_outstanding"]

    wacc_info = compute_wacc(assumptions, market_cap=market_cap, gross_debt=gross_debt)
    wacc = wacc_info["wacc"]

    terminal_growth = assumptions.terminal_growth
    if terminal_growth >= wacc:
        clipped = max(0.0, wacc - _TERMINAL_GROWTH_BUFFER)
        warnings.append(
            f"Terminal growth ({terminal_growth:.1%}) was >= WACC ({wacc:.1%}); clipped to "
            f"{clipped:.1%} so the Gordon growth model stays well-defined."
        )
        terminal_growth = clipped

    proj_assumptions = assumptions if terminal_growth == assumptions.terminal_growth else replace(
        assumptions, terminal_growth=terminal_growth
    )
    rows = project_fcff(proj_assumptions, base_revenue)

    years: list[YearProjection] = []
    pv_sum = 0.0
    for row in rows:
        discount_factor = 1.0 / ((1.0 + wacc) ** row["year"])
        pv_fcff = row["fcff"] * discount_factor
        pv_sum += pv_fcff
        years.append(YearProjection(discount_factor=discount_factor, pv_fcff=pv_fcff, **row))

    last_fcff = rows[-1]["fcff"] if rows else 0.0
    if wacc > terminal_growth:
        terminal_value = last_fcff * (1 + terminal_growth) / (wacc - terminal_growth)
    else:
        terminal_value = 0.0
        warnings.append("WACC <= terminal growth even after clipping; terminal value set to 0.")
    pv_terminal_value = terminal_value * (years[-1].discount_factor if years else 0.0)

    enterprise_value = pv_sum + pv_terminal_value
    equity_value = enterprise_value - net_debt if net_debt is not None else None

    shares = market.get("shares_outstanding")
    value_per_share: float | None = None
    if equity_value is not None and shares:
        value_per_share = equity_value / shares
    elif equity_value is not None:
        warnings.append("Shares outstanding unavailable; cannot compute per-share value.")

    price = market.get("price")
    upside_pct = value_per_share / price - 1.0 if value_per_share is not None and price else None

    return DcfResult(
        ticker=ticker.upper(),
        assumptions=assumptions,
        base_revenue=base_revenue,
        years=years,
        cost_of_equity=wacc_info["cost_of_equity"],
        after_tax_cost_of_debt=wacc_info["after_tax_cost_of_debt"],
        equity_weight=wacc_info["equity_weight"],
        debt_weight=wacc_info["debt_weight"],
        wacc=wacc,
        wacc_source=wacc_info["source"],
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal_value,
        enterprise_value=enterprise_value,
        net_debt=net_debt,
        equity_value=equity_value,
        shares_outstanding=shares,
        value_per_share=value_per_share,
        current_price=price,
        upside_pct=upside_pct,
        warnings=warnings,
    )


def sensitivity_grid(
    ticker: str,
    assumptions: DcfAssumptions,
    *,
    wacc_deltas: tuple[float, ...] = (-0.02, -0.01, 0.0, 0.01, 0.02),
    growth_deltas: tuple[float, ...] = (-0.01, -0.005, 0.0, 0.005, 0.01),
) -> dict[str, Any]:
    """Value-per-share (or EV, if shares are unavailable) across a WACC x terminal-growth grid."""
    hist = build_annual_history(ticker)
    kpis = extract_kpis(ticker)
    market = fetch_market_data(ticker)

    base = discount_cash_flow(ticker, assumptions, _hist=hist, _kpis=kpis, _market=market)
    metric = "value_per_share" if base.value_per_share is not None else "enterprise_value"
    wacc_values = [base.wacc + d for d in wacc_deltas]
    growth_values = [assumptions.terminal_growth + d for d in growth_deltas]

    grid: list[list[float]] = []
    for w in wacc_values:
        row: list[float] = []
        for g in growth_values:
            variant = replace(assumptions, wacc_override=w, terminal_growth=g)
            result = discount_cash_flow(ticker, variant, _hist=hist, _kpis=kpis, _market=market)
            row.append(getattr(result, metric))
        grid.append(row)

    return {
        "metric": metric,
        "wacc_values": wacc_values,
        "growth_values": growth_values,
        "grid": grid,
    }
