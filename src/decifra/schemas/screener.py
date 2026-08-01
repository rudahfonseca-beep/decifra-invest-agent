"""Cross-asset opportunity screener rows from APV + Merton + capacity (IMP-038)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from decifra.credit.assemble_models import assemble_capacity, assemble_merton
from decifra.http_util import normalize_ticker
from decifra.store.folders import list_tickers, load_identity
from decifra.valuation.assemble_apv import assemble_apv
from decifra.valuation.market_data import fetch_market_data

Signal = Literal["safe", "warning", "distress"]


def _signal(
    *,
    apv_discount_pct: float | None,
    nd_ebitda: float | None,
    dscr: float | None,
    merton_pd: float | None,
    any_breach: bool,
) -> Signal:
    if any_breach or (merton_pd is not None and merton_pd >= 0.10) or (dscr is not None and dscr < 1.0):
        return "distress"
    if (
        (nd_ebitda is not None and nd_ebitda >= 3.0)
        or (merton_pd is not None and merton_pd >= 0.03)
        or (dscr is not None and dscr < 1.25)
        or (apv_discount_pct is not None and apv_discount_pct < 0)
    ):
        return "warning"
    return "safe"


def assemble_screener_row(ticker: str) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    ident = load_identity(t)
    market = fetch_market_data(t)

    apv_pack = assemble_apv(t)
    cap_pack = assemble_capacity(t)
    merton_pack = assemble_merton(t)

    apv_discount = apv_pack.get("apv_discount_pct")
    # Store as percent points for UI (18.4 not 0.184)
    apv_discount_pct = float(apv_discount) * 100.0 if apv_discount is not None else None

    cap = cap_pack.get("capacity") or {}
    nd_flag = cap.get("net_debt_ebitda") or {}
    dscr_flag = cap.get("dscr") or {}
    nd_ebitda = nd_flag.get("value") if isinstance(nd_flag, dict) else None
    dscr = dscr_flag.get("value") if isinstance(dscr_flag, dict) else None
    any_breach = bool(cap.get("any_breach"))

    merton = merton_pack.get("merton") or {}
    merton_pd = merton.get("default_probability") if merton else None
    merton_pd_pct = float(merton_pd) * 100.0 if merton_pd is not None else None

    market_cap = market.get("market_cap") or apv_pack.get("market_cap")
    v_l = (apv_pack.get("apv") or {}).get("v_l")
    ev_equity = None
    if v_l is not None and market_cap and market_cap > 0:
        ev_equity = float(v_l) / float(market_cap)

    period = (cap_pack.get("lineage") or {}).get("period") or ""
    equity_fresh = f"ITR/DFP {period}" if period else (apv_pack.get("lineage") or {}).get("freshness", "lake")
    credit_fresh = (merton_pack.get("lineage") or {}).get("freshness") or "capacity+merton"

    signal = _signal(
        apv_discount_pct=apv_discount,
        nd_ebitda=nd_ebitda,
        dscr=dscr,
        merton_pd=merton_pd,
        any_breach=any_breach,
    )

    return {
        "ticker": t,
        "cnpj": ident.get("cnpj") or "",
        "isin": (ident.get("isins") or [""])[0] if ident.get("isins") else "",
        "company_name": ident.get("company_name") or ident.get("stock_name") or t,
        "apv_discount_pct": apv_discount_pct,
        "ev_equity": ev_equity,
        "net_debt_ebitda": nd_ebitda,
        "dscr": dscr,
        "merton_pd_pct": merton_pd_pct,
        "signal": signal,
        "lineage": {
            "equity": equity_fresh,
            "credit": credit_fresh,
        },
    }


def assemble_opportunity_screener(
    tickers: list[str] | None = None,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build screener payload for React / API."""
    names = [normalize_ticker(t) for t in (tickers or list_tickers())]
    if limit is not None:
        names = names[:limit]
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for t in names:
        try:
            rows.append(assemble_screener_row(t))
        except Exception as exc:  # pragma: no cover - lake gaps
            errors.append({"ticker": t, "error": str(exc)})
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "errors": errors,
    }


def assemble_catalyst_feed(screener: dict[str, Any] | None = None) -> dict[str, Any]:
    """Derive a simple catalyst timeline from screener signals + capacity breaches."""
    payload = screener or assemble_opportunity_screener(limit=12)
    items: list[dict[str, Any]] = []
    for i, row in enumerate(payload.get("rows") or []):
        sig = row.get("signal") or "safe"
        if sig == "safe" and i > 4:
            continue
        title = f"{row['ticker']} — "
        if sig == "distress":
            title += "Capacity / default stress signal"
            impact = (
                f"ND/EBITDA={row.get('net_debt_ebitda')}; DSCR={row.get('dscr')}; "
                f"Merton PD={row.get('merton_pd_pct')}%"
            )
            source = "Capacity+Merton"
        elif sig == "warning":
            title += "Watch: leverage or APV discount"
            impact = (
                f"APV disc={row.get('apv_discount_pct')}%; "
                f"ND/EBITDA={row.get('net_debt_ebitda')}"
            )
            source = "APV+Capacity"
        else:
            title += "Stable credit / APV upside"
            impact = f"APV disc={row.get('apv_discount_pct')}%; DSCR={row.get('dscr')}"
            source = "CVM ITR"
        items.append(
            {
                "id": f"cat-{row['ticker'].lower()}",
                "source": source,
                "ts_relative": "assembled just now",
                "title": title,
                "impact": impact,
                "signal": sig,
            }
        )
    return {"items": items}
