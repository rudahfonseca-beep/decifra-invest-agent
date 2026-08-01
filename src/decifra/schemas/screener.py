"""Cross-asset opportunity screener rows from APV + Merton + capacity (IMP-038)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Literal

from decifra.credit.assemble_models import assemble_capacity, assemble_merton
from decifra.http_util import normalize_ticker
from decifra.schemas.ui_cache import disk_get_or_set, ttl_get_or_set
from decifra.store.folders import list_tickers, load_identity
from decifra.valuation.assemble_apv import assemble_apv
from decifra.valuation.market_data import fetch_market_data

Signal = Literal["safe", "warning", "distress"]

_DEFAULT_WORKERS = 8


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


def _assemble_rows_parallel(names: list[str], *, workers: int = _DEFAULT_WORKERS) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    if not names:
        return rows, errors
    max_workers = max(1, min(workers, len(names)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(assemble_screener_row, t): t for t in names}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                rows.append(fut.result())
            except Exception as exc:  # pragma: no cover - lake gaps
                errors.append({"ticker": t, "error": str(exc)})
    rows.sort(key=lambda r: r.get("ticker") or "")
    return rows, errors


def assemble_opportunity_screener(
    tickers: list[str] | None = None,
    *,
    limit: int | None = None,
    offset: int = 0,
    refresh: bool = False,
    scope: str = "core",
    q: str | None = None,
    persist_disk: bool = True,
    workers: int = _DEFAULT_WORKERS,
) -> dict[str, Any]:
    """Build screener payload for React / API (TTL + optional disk cache)."""
    names = [normalize_ticker(t) for t in (tickers or list_tickers(scope=scope))]  # type: ignore[arg-type]
    if q:
        needle = q.strip().upper()
        names = [t for t in names if needle in t]
    total = len(names)
    start = max(0, offset)
    page = names[start:]
    if limit is not None:
        page = page[:limit]
    cache_key = f"screener:{scope}:{limit}:{offset}:{q or ''}:{','.join(page)}"
    disk_name = f"screener_{scope}"

    def _build() -> dict[str, Any]:
        rows, errors = _assemble_rows_parallel(page, workers=workers)
        return {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "scope": scope,
            "q": q or "",
            "offset": offset,
            "limit": limit,
            "total": total,
            "rows": rows,
            "errors": errors,
        }

    if persist_disk and tickers is None and offset == 0 and not q and limit is None:
        # Full-scope warm artifact for serve start / sync_pilot
        return disk_get_or_set(
            disk_name,
            _build,
            memory_key=cache_key,
            refresh=refresh,
        )
    return ttl_get_or_set(cache_key, _build, refresh=refresh)


def assemble_catalyst_feed(
    screener: dict[str, Any] | None = None,
    *,
    limit: int = 12,
    refresh: bool = False,
    scope: str = "core",
) -> dict[str, Any]:
    """Derive a simple catalyst timeline from screener signals + capacity breaches."""
    if screener is not None:
        return _catalyst_items(screener)

    def _from_screener() -> dict[str, Any]:
        return _catalyst_items(
            assemble_opportunity_screener(limit=limit, refresh=refresh, scope=scope)
        )

    return ttl_get_or_set(f"catalysts:{scope}:{limit}", _from_screener, refresh=refresh)


def _catalyst_items(payload: dict[str, Any]) -> dict[str, Any]:
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
