"""Trading multiples (P/E, EV/EBITDA, EV/Revenue, EV/EBIT, P/B) and relative valuation.

Multiples are built from the same local sources as the DCF engine
(`valuation.historical` for financials, `valuation.market_data` for live
price/shares) so both valuation methods triangulate off the same underlying
data. Comparable selection is entirely up to the caller — the credit
module's `industry_group()` is only used upstream (spec/dashboard layer) to
*suggest* a default peer set; any ticker in the local universe can be added.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from decifra.store.folders import load_meta
from decifra.valuation.historical import build_annual_history
from decifra.valuation.market_data import fetch_market_data

MULTIPLE_LABELS: dict[str, str] = {
    "pe": "P/E",
    "ev_ebitda": "EV/EBITDA",
    "ev_revenue": "EV/Revenue",
    "ev_ebit": "EV/EBIT",
    "pb": "P/B",
}


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


@dataclass
class CompanyMultiples:
    ticker: str
    company: str
    price: float | None
    shares_outstanding: float | None
    market_cap: float | None
    gross_debt: float | None
    net_debt: float | None
    enterprise_value: float | None
    revenue: float | None
    ebit: float | None
    ebitda: float | None
    net_income: float | None
    equity: float | None
    pe: float | None
    ev_ebitda: float | None
    ev_revenue: float | None
    ev_ebit: float | None
    pb: float | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_multiples(ticker: str) -> CompanyMultiples:
    """P/E, EV/EBITDA, EV/Revenue, EV/EBIT, P/B for one ticker from local data + live quote."""
    hist = build_annual_history(ticker)
    meta = load_meta(ticker)
    market = fetch_market_data(ticker)
    warnings: list[str] = []

    latest = hist.iloc[-1] if not hist.empty else pd.Series(dtype=float)

    def _get(col: str) -> float | None:
        val = latest.get(col) if not latest.empty else None
        return float(val) if val is not None and pd.notna(val) else None

    revenue = _get("revenue")
    ebit = _get("ebit")
    da = _get("depreciation_amortization")
    net_income = _get("net_income_controllers")
    if net_income is None:
        net_income = _get("net_income")
    equity = _get("equity")
    gross_debt = _get("gross_debt")
    net_debt = _get("net_debt")
    ebitda = (ebit + da) if (ebit is not None and da is not None) else None

    price = market.get("price")
    shares = market.get("shares_outstanding")
    market_cap = market.get("market_cap")
    if market_cap is None and price and shares:
        market_cap = price * shares
    if market_cap is None:
        warnings.append("Market cap unavailable; EV- and P/E-based multiples cannot be computed.")

    enterprise_value: float | None = None
    if market_cap is not None and net_debt is not None:
        enterprise_value = market_cap + net_debt
    elif market_cap is not None and gross_debt is not None:
        enterprise_value = market_cap + gross_debt
        warnings.append("Net debt unavailable; enterprise value uses gross debt only (ignores cash).")

    if net_income is not None and net_income <= 0:
        warnings.append("Net income is zero/negative; P/E is not meaningful.")

    pe = _safe_div(market_cap, net_income) if (net_income and net_income > 0) else None
    ev_ebitda = _safe_div(enterprise_value, ebitda) if (ebitda and ebitda > 0) else None
    ev_revenue = _safe_div(enterprise_value, revenue) if (revenue and revenue > 0) else None
    ev_ebit = _safe_div(enterprise_value, ebit) if (ebit and ebit > 0) else None
    pb = _safe_div(market_cap, equity) if (equity and equity > 0) else None

    company = meta.get("company_name") or meta.get("stock_name") or ticker.upper()

    return CompanyMultiples(
        ticker=ticker.upper(),
        company=company,
        price=price,
        shares_outstanding=shares,
        market_cap=market_cap,
        gross_debt=gross_debt,
        net_debt=net_debt,
        enterprise_value=enterprise_value,
        revenue=revenue,
        ebit=ebit,
        ebitda=ebitda,
        net_income=net_income,
        equity=equity,
        pe=pe,
        ev_ebitda=ev_ebitda,
        ev_revenue=ev_revenue,
        ev_ebit=ev_ebit,
        pb=pb,
        warnings=warnings,
    )


def _aggregate(values: list[float], stat: str) -> float | None:
    s = pd.Series(values, dtype=float).dropna()
    if s.empty:
        return None
    return float(s.median()) if stat == "median" else float(s.mean())


@dataclass
class RelativeValuation:
    ticker: str
    stat: str
    peer_count: int
    peer_benchmark: bool
    subject: CompanyMultiples
    peers: list[CompanyMultiples]
    peer_multiples: dict[str, float | None]
    implied_price: dict[str, float | None]
    implied_price_low: float | None
    implied_price_high: float | None
    implied_price_avg: float | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def relative_valuation(
    ticker: str, peers: list[str], *, stat: str = "median"
) -> RelativeValuation:
    """Apply peer multiples (median by default) to the subject's own fundamentals.

    `peers` is entirely user-chosen — the caller (CLI/dashboard) decides
    whether to seed it from the same `industry_group()` or pick any other
    tickers in the local universe.
    """
    if stat not in {"median", "mean"}:
        raise ValueError(f"Unsupported stat '{stat}'; expected 'median' or 'mean'")

    subject = compute_multiples(ticker)
    peer_objs = [compute_multiples(p) for p in peers if p.upper() != subject.ticker]
    warnings = list(subject.warnings)

    peer_multiples: dict[str, float | None] = {}
    for key in MULTIPLE_LABELS:
        values = [getattr(p, key) for p in peer_objs if getattr(p, key) is not None]
        peer_multiples[key] = _aggregate(values, stat)

    shares = subject.shares_outstanding
    if not shares:
        warnings.append("Subject shares outstanding unavailable; cannot compute implied per-share values.")

    def _implied_from_earnings(key: str, base: float | None) -> float | None:
        m = peer_multiples.get(key)
        if m is None or base is None or not shares:
            return None
        return (m * base) / shares

    def _implied_from_ev(key: str, base: float | None) -> float | None:
        m = peer_multiples.get(key)
        if m is None or base is None or not shares:
            return None
        implied_ev = m * base
        implied_equity = implied_ev - (subject.net_debt or 0.0)
        return implied_equity / shares

    implied_price: dict[str, float | None] = {
        "pe": _implied_from_earnings("pe", subject.net_income),
        "pb": _implied_from_earnings("pb", subject.equity),
        "ev_ebitda": _implied_from_ev("ev_ebitda", subject.ebitda),
        "ev_revenue": _implied_from_ev("ev_revenue", subject.revenue),
        "ev_ebit": _implied_from_ev("ev_ebit", subject.ebit),
    }

    valid_prices = [v for v in implied_price.values() if v is not None and v > 0]
    implied_avg = float(sum(valid_prices) / len(valid_prices)) if valid_prices else None
    implied_low = min(valid_prices) if valid_prices else None
    implied_high = max(valid_prices) if valid_prices else None

    peer_count = len(peer_objs)
    if peer_count < 2:
        warnings.append(
            f"Only {peer_count} comparable(s) selected; multiples are directional, not a robust benchmark."
        )

    return RelativeValuation(
        ticker=subject.ticker,
        stat=stat,
        peer_count=peer_count,
        peer_benchmark=peer_count >= 2,
        subject=subject,
        peers=peer_objs,
        peer_multiples=peer_multiples,
        implied_price=implied_price,
        implied_price_low=implied_low,
        implied_price_high=implied_high,
        implied_price_avg=implied_avg,
        warnings=warnings,
    )
