"""Default DCF assumption construction with a traceable "why" for every number.

Nothing here is a black box: `build_default_assumptions()` returns both the
computed `DcfAssumptions` and a list of `AssumptionNote` records describing
exactly which historical figures / formula produced each default, so the
Streamlit UI and persisted artifacts can show "how these numbers were built"
with this specific company's own data.

See `docs/workflows/valuation.md` for the full methodology writeup.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from decifra.config import (
    CORPORATE_TAX_RATE_DEFAULT,
    COUNTRY_RISK_PREMIUM_DEFAULT,
    DEFAULT_BETA,
    DEFAULT_FORECAST_YEARS,
    EQUITY_RISK_PREMIUM_DEFAULT,
    FINANCIAL_TAX_RATE_DEFAULT,
    RISK_FREE_RATE_DEFAULT,
    TERMINAL_GROWTH_DEFAULT,
)
from decifra.credit.metrics import extract_kpis
from decifra.credit.scoring import FINANCIAL_GROUPS, industry_group
from decifra.valuation.historical import build_annual_history, cagr, trailing_average, trailing_median
from decifra.valuation.market_data import compute_regression_beta, fetch_market_data

# Damodaran-style synthetic spread table: EBIT interest coverage -> spread over Rf.
# Used as the cost-of-debt fallback when a company's own effective interest
# rate is missing or implausible (e.g. no reported debt, or a one-off rate).
_COVERAGE_SPREAD_TABLE: list[tuple[float, float]] = [
    (8.5, 0.010),
    (6.5, 0.013),
    (5.5, 0.017),
    (4.25, 0.021),
    (3.0, 0.028),
    (2.5, 0.035),
    (2.0, 0.045),
    (1.5, 0.060),
    (1.25, 0.075),
    (0.8, 0.090),
    (0.5, 0.115),
]
_COVERAGE_SPREAD_FLOOR = 0.150
_DEFAULT_SPREAD_NO_COVERAGE = 0.060

# Sane bounds so a single noisy historical figure can't produce a nonsensical default
_REVENUE_GROWTH_BAND = (-0.20, 0.40)
_TAX_RATE_BAND = (0.10, 0.45)
_MARGIN_BAND = (-0.10, 0.60)
_BETA_SANITY_BAND = (0.2, 3.0)
_COST_OF_DEBT_SANITY_BAND = (0.01, 0.35)


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class AssumptionNote:
    """One traceable "how this default was built" entry."""

    key: str
    label: str
    value: float | None
    formula: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DcfAssumptions:
    forecast_years: int = DEFAULT_FORECAST_YEARS
    revenue_growth_y1: float = 0.05
    terminal_growth: float = TERMINAL_GROWTH_DEFAULT
    ebit_margin: float = 0.10
    tax_rate: float = CORPORATE_TAX_RATE_DEFAULT
    da_pct_revenue: float = 0.04
    capex_pct_revenue: float = 0.05
    nwc_pct_revenue: float = 0.0
    risk_free_rate: float = RISK_FREE_RATE_DEFAULT
    equity_risk_premium: float = EQUITY_RISK_PREMIUM_DEFAULT
    country_risk_premium: float = COUNTRY_RISK_PREMIUM_DEFAULT
    beta: float = DEFAULT_BETA
    cost_of_debt: float = 0.09
    wacc_override: float | None = None  # bypasses CAPM + weights entirely when set

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DcfAssumptions":
        base = cls()
        for k, v in (data or {}).items():
            if hasattr(base, k) and v is not None:
                setattr(base, k, v)
        return base


def _resolve_beta(
    ticker: str, market_beta: float | None, *, peers: list[str] | None = None
) -> tuple[float, str, str]:
    """Beta fallback chain: Yahoo info -> local regression -> peer average -> neutral 1.0."""
    if market_beta is not None and _BETA_SANITY_BAND[0] <= market_beta <= _BETA_SANITY_BAND[1]:
        return market_beta, "yfinance info", f"Provider-reported beta {market_beta:.2f}."

    reg_beta, n_obs = compute_regression_beta(ticker)
    if reg_beta is not None and _BETA_SANITY_BAND[0] <= reg_beta <= _BETA_SANITY_BAND[1]:
        return (
            reg_beta,
            "local regression",
            f"OLS slope of weekly returns vs. Ibovespa (^BVSP) over {n_obs} weeks = {reg_beta:.2f}.",
        )

    if peers:
        peer_betas: list[float] = []
        for p in peers:
            if p.upper() == ticker.upper():
                continue
            md = fetch_market_data(p)
            b = md.get("beta")
            if b is None or not (_BETA_SANITY_BAND[0] <= b <= _BETA_SANITY_BAND[1]):
                b, _ = compute_regression_beta(p)
            if b is not None and _BETA_SANITY_BAND[0] <= b <= _BETA_SANITY_BAND[1]:
                peer_betas.append(b)
        if peer_betas:
            avg = sum(peer_betas) / len(peer_betas)
            return (
                avg,
                "peer average",
                f"Average beta of {len(peer_betas)} comparable(s) ({', '.join(peers[:len(peer_betas)])}) = {avg:.2f}.",
            )

    return (
        DEFAULT_BETA,
        "neutral default",
        "Insufficient price history for this ticker or its comparables; using market-neutral beta = 1.0.",
    )


def _resolve_cost_of_debt(
    kpis: dict[str, Any], risk_free_rate: float
) -> tuple[float, str, str]:
    """Company's own effective rate when sane, else a synthetic spread from interest coverage."""
    interest_expense = kpis.get("interest_expense")
    gross_debt = kpis.get("gross_debt")
    if interest_expense is not None and gross_debt and gross_debt > 0:
        own_rate = abs(interest_expense) / gross_debt
        if _COST_OF_DEBT_SANITY_BAND[0] <= own_rate <= _COST_OF_DEBT_SANITY_BAND[1]:
            return (
                own_rate,
                "own effective rate",
                f"|interest_expense| / gross_debt = {abs(interest_expense):,.0f} / {gross_debt:,.0f} = {own_rate:.1%}.",
            )

    coverage = kpis.get("interest_coverage")
    if coverage is not None:
        spread = _COVERAGE_SPREAD_FLOOR
        for threshold, s in _COVERAGE_SPREAD_TABLE:
            if coverage >= threshold:
                spread = s
                break
        rate = risk_free_rate + spread
        return (
            rate,
            "synthetic spread (interest coverage)",
            f"Interest coverage {coverage:.1f}x -> Damodaran-style spread {spread:.1%} over risk-free "
            f"{risk_free_rate:.1%} = {rate:.1%}.",
        )

    rate = risk_free_rate + _DEFAULT_SPREAD_NO_COVERAGE
    return (
        rate,
        "default spread",
        f"No usable interest expense/coverage data; risk-free {risk_free_rate:.1%} + "
        f"default mid-market spread {_DEFAULT_SPREAD_NO_COVERAGE:.1%} = {rate:.1%}.",
    )


def build_default_assumptions(
    ticker: str,
    *,
    peers: list[str] | None = None,
    forecast_years: int = DEFAULT_FORECAST_YEARS,
) -> tuple[DcfAssumptions, list[AssumptionNote]]:
    """Data-grounded default DCF assumptions for `ticker`, with a traceable rationale per field."""
    hist = build_annual_history(ticker)
    kpis = extract_kpis(ticker)
    market = fetch_market_data(ticker)
    cohort_financial = industry_group(kpis.get("sector") or "") in FINANCIAL_GROUPS

    notes: list[AssumptionNote] = []

    # --- Revenue growth: blend of 3y/5y CAGR, clipped to a sane band ---
    g3 = cagr(hist, "revenue", 3)
    g5 = cagr(hist, "revenue", 5)
    candidates = [g for g in (g3, g5) if g is not None]
    if candidates:
        growth_raw = sum(candidates) / len(candidates)
        growth = _clip(growth_raw, *_REVENUE_GROWTH_BAND)
        parts = []
        if g3 is not None:
            parts.append(f"3y CAGR {g3:.1%}")
        if g5 is not None:
            parts.append(f"5y CAGR {g5:.1%}")
        notes.append(
            AssumptionNote(
                "revenue_growth_y1",
                "Year-1 revenue growth",
                growth,
                f"mean({', '.join(parts)}) = {growth_raw:.1%}, clipped to [{_REVENUE_GROWTH_BAND[0]:.0%}, {_REVENUE_GROWTH_BAND[1]:.0%}]",
                "Blends short- and medium-term historical growth; clipped so one-off "
                "commodity/FX cycles don't extrapolate into an unrealistic forecast. "
                "Fades linearly toward the terminal growth rate over the forecast horizon.",
            )
        )
    else:
        growth = 0.05
        notes.append(
            AssumptionNote(
                "revenue_growth_y1",
                "Year-1 revenue growth",
                growth,
                "no usable multi-year revenue history",
                "Fewer than 2 annual filings available locally; using a neutral 5% "
                "placeholder — override once more history is synced.",
            )
        )

    # --- EBIT margin: median of trailing 5y (fallback 3y), robust to one-off shocks ---
    margin = trailing_median(hist, "ebit_margin", 5) or trailing_median(hist, "ebit_margin", 3)
    if margin is not None:
        margin = _clip(margin, *_MARGIN_BAND)
        notes.append(
            AssumptionNote(
                "ebit_margin",
                "EBIT margin",
                margin,
                "median(EBIT / revenue) over up to 5 fiscal years",
                "Median (not mean or latest-year) so a single cyclical/impairment year "
                "doesn't dominate the forecast margin.",
            )
        )
    else:
        margin = 0.10
        notes.append(
            AssumptionNote(
                "ebit_margin",
                "EBIT margin",
                margin,
                "no usable historical EBIT margin",
                "No annual EBIT/revenue history available; using a neutral 10% placeholder.",
            )
        )

    # --- Tax rate: 3y average effective rate, floored/capped to the statutory band ---
    tax_band = (
        (_TAX_RATE_BAND[0], FINANCIAL_TAX_RATE_DEFAULT)
        if cohort_financial
        else (_TAX_RATE_BAND[0], CORPORATE_TAX_RATE_DEFAULT + 0.05)
    )
    eff_tax = trailing_average(hist, "effective_tax_rate", 3)
    statutory = FINANCIAL_TAX_RATE_DEFAULT if cohort_financial else CORPORATE_TAX_RATE_DEFAULT
    if eff_tax is not None and eff_tax > 0:
        tax_rate = _clip(eff_tax, *tax_band)
        notes.append(
            AssumptionNote(
                "tax_rate",
                "Effective tax rate",
                tax_rate,
                f"avg(-tax_expense / pretax_income) over 3y = {eff_tax:.1%}, clipped to [{tax_band[0]:.0%}, {tax_band[1]:.0%}]",
                "3y average smooths one-off deferred-tax credits/debits; clipped to the "
                f"Brazilian statutory band ({'financial cohort ~45%' if cohort_financial else '~34%'}).",
            )
        )
    else:
        tax_rate = statutory
        notes.append(
            AssumptionNote(
                "tax_rate",
                "Effective tax rate",
                tax_rate,
                "no usable historical effective tax rate",
                f"Using the Brazilian statutory rate ({statutory:.0%}) for this cohort.",
            )
        )

    # --- D&A, Capex, NWC as % of revenue: trailing averages (capital intensity) ---
    da_pct = trailing_average(hist, "da_pct_revenue", 5) or trailing_average(hist, "da_pct_revenue", 3)
    if da_pct is None:
        da_pct = 0.04
        da_formula, da_rationale = (
            "no usable historical D&A",
            "No D&A history available; using a neutral 4% of revenue placeholder.",
        )
    else:
        da_formula = "avg(D&A / revenue) over up to 5 fiscal years"
        da_rationale = "Captures this company's own capital intensity from its cash-flow statement."
    notes.append(AssumptionNote("da_pct_revenue", "D&A (% revenue)", da_pct, da_formula, da_rationale))

    capex_pct = trailing_average(hist, "capex_pct_revenue", 5) or trailing_average(hist, "capex_pct_revenue", 3)
    if capex_pct is None:
        capex_pct = 0.05
        capex_formula, capex_rationale = (
            "no usable historical capex",
            "No capex history available; using a neutral 5% of revenue placeholder.",
        )
    else:
        capex_formula = "avg(capex / revenue) over up to 5 fiscal years"
        capex_rationale = (
            "Historical reinvestment rate; the terminal year instead sets capex ≈ D&A "
            "(steady-state reinvestment for a mature/stable firm)."
        )
    notes.append(AssumptionNote("capex_pct_revenue", "Capex (% revenue)", capex_pct, capex_formula, capex_rationale))

    nwc_pct = trailing_average(hist, "nwc_pct_revenue", 5) or trailing_average(hist, "nwc_pct_revenue", 3)
    if nwc_pct is None:
        nwc_pct = 0.0
        nwc_formula, nwc_rationale = (
            "no usable historical working-capital cash effect",
            "No cash-flow-statement working-capital history available; assuming no incremental NWC drag.",
        )
    else:
        nwc_formula = "avg(-cash-flow working-capital effect / revenue) over up to 5 fiscal years"
        nwc_rationale = (
            "Taken directly from the CF statement's 'Variações nos Ativos e Passivos' line "
            "(more reliable than re-deriving from balance-sheet deltas); applied to each "
            "year's revenue increase in the projection."
        )
    notes.append(AssumptionNote("nwc_pct_revenue", "ΔNWC (% of revenue growth)", nwc_pct, nwc_formula, nwc_rationale))

    # --- Terminal growth: static macro proxy, always below WACC (enforced in dcf.py) ---
    terminal_growth = TERMINAL_GROWTH_DEFAULT
    notes.append(
        AssumptionNote(
            "terminal_growth",
            "Terminal growth rate",
            terminal_growth,
            "config default (long-run BRL nominal GDP + inflation proxy)",
            "Static macro assumption — refresh periodically; this project has no live "
            "macro feed. Always kept below WACC.",
        )
    )

    # --- Cost of equity inputs: Rf, ERP, CRP (static config proxies) + beta (data-driven) ---
    risk_free_rate = RISK_FREE_RATE_DEFAULT
    erp = EQUITY_RISK_PREMIUM_DEFAULT
    crp = COUNTRY_RISK_PREMIUM_DEFAULT
    notes.append(
        AssumptionNote(
            "risk_free_rate",
            "Risk-free rate",
            risk_free_rate,
            "config default",
            "Static proxy for a long Brazilian sovereign yield (e.g. NTN-B). Refresh via "
            "DECIFRA_RISK_FREE_RATE or override per run.",
        )
    )
    notes.append(
        AssumptionNote(
            "equity_risk_premium",
            "Equity risk premium",
            erp,
            "config default",
            "Static mature-market ERP proxy (Damodaran-style). Refresh via "
            "DECIFRA_EQUITY_RISK_PREMIUM.",
        )
    )
    notes.append(
        AssumptionNote(
            "country_risk_premium",
            "Country risk premium",
            crp,
            "config default",
            "Static Brazil sovereign-spread proxy, added on top of the mature-market ERP.",
        )
    )

    beta, beta_source, beta_rationale = _resolve_beta(ticker, market.get("beta"), peers=peers)
    notes.append(AssumptionNote("beta", f"Beta ({beta_source})", beta, beta_source, beta_rationale))

    cost_of_debt, kd_source, kd_rationale = _resolve_cost_of_debt(kpis, risk_free_rate)
    notes.append(AssumptionNote("cost_of_debt", f"Pre-tax cost of debt ({kd_source})", cost_of_debt, kd_source, kd_rationale))

    assumptions = DcfAssumptions(
        forecast_years=forecast_years,
        revenue_growth_y1=growth,
        terminal_growth=terminal_growth,
        ebit_margin=margin,
        tax_rate=tax_rate,
        da_pct_revenue=da_pct,
        capex_pct_revenue=capex_pct,
        nwc_pct_revenue=nwc_pct,
        risk_free_rate=risk_free_rate,
        equity_risk_premium=erp,
        country_risk_premium=crp,
        beta=beta,
        cost_of_debt=cost_of_debt,
    )
    return assumptions, notes
