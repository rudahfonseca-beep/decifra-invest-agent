"""Live market data (price, shares outstanding, market cap) with local caching,
plus Ibovespa index history for beta regression.

Market quotes are **not** part of the CVM/B3 sync pipeline (`decifra sync
...`); they are fetched on demand by the valuation layer and cached under
`financials/market_data.json` (per company) and `data/cache/market/` (shared
index series), refreshed after `MARKET_DATA_CACHE_HOURS`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from decifra.config import (
    BETA_LOOKBACK_YEARS,
    IBOVESPA_INDEX_TICKER,
    MARKET_CACHE_DIR,
    MARKET_DATA_CACHE_HOURS,
)
from decifra.http_util import normalize_ticker
from decifra.store.folders import company_dir


def _market_data_path(ticker: str) -> Path:
    return company_dir(ticker) / "financials" / "market_data.json"


def _is_fresh(fetched_at: str, max_age_hours: float) -> bool:
    try:
        ts = datetime.fromisoformat(fetched_at)
    except (TypeError, ValueError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts < timedelta(hours=max_age_hours)


def _fetch_yfinance_quote(ticker: str) -> dict[str, Any]:
    import yfinance as yf

    t = normalize_ticker(ticker)
    yt = yf.Ticker(f"{t}.SA")

    price: float | None = None
    try:
        fast = yt.fast_info
        price = fast.get("lastPrice") or fast.get("last_price")
    except Exception:
        price = None

    shares: float | None = None
    market_cap: float | None = None
    beta: float | None = None
    try:
        info = yt.info or {}
    except Exception:
        info = {}
    if info:
        if not price:
            price = info.get("currentPrice") or info.get("regularMarketPrice")
        shares = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")
        beta = info.get("beta")

    if price and market_cap is None and shares:
        market_cap = float(price) * float(shares)

    return {
        "price": float(price) if price else None,
        "shares_outstanding": float(shares) if shares else None,
        "market_cap": float(market_cap) if market_cap else None,
        "beta": float(beta) if beta not in (None, 0) else None,
        "source": "yfinance",
    }


def fetch_market_data(ticker: str, *, force: bool = False) -> dict[str, Any]:
    """Return `{price, shares_outstanding, market_cap, beta, source, fetched_at, stale}`.

    Cached per company under `financials/market_data.json`; refreshed when
    older than `MARKET_DATA_CACHE_HOURS` or when `force=True`. Any field may
    be `None` if the upstream quote provider has nothing for this ticker —
    callers must degrade gracefully (EV-based figures can still be shown;
    per-share figures cannot without `shares_outstanding`).
    """
    path = _market_data_path(ticker)
    if not force and path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if _is_fresh(cached.get("fetched_at", ""), MARKET_DATA_CACHE_HOURS):
                cached["stale"] = False
                return cached
        except (json.JSONDecodeError, OSError):
            pass

    data: dict[str, Any] = {
        "ticker": normalize_ticker(ticker),
        "price": None,
        "shares_outstanding": None,
        "market_cap": None,
        "beta": None,
        "source": "unavailable",
    }
    try:
        data.update(_fetch_yfinance_quote(ticker))
    except Exception:
        pass

    data["fetched_at"] = datetime.now(timezone.utc).isoformat()
    data["stale"] = data.get("price") is None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return data


def _index_cache_path() -> Path:
    return MARKET_CACHE_DIR / "ibovespa_index.csv"


def fetch_index_history(*, force: bool = False, max_age_hours: float = 24.0) -> pd.DataFrame:
    """Cached Ibovespa (`^BVSP`) daily close history — the market proxy used for beta."""
    path = _index_cache_path()
    if not force and path.exists():
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if datetime.now(timezone.utc) - mtime < timedelta(hours=max_age_hours):
                return pd.read_csv(path, parse_dates=["date"])
        except OSError:
            pass

    try:
        import yfinance as yf

        hist = yf.Ticker(IBOVESPA_INDEX_TICKER).history(period="10y", auto_adjust=False)
        if hist.empty:
            raise ValueError("empty index history")
        hist = hist.reset_index()[["Date", "Close"]].rename(columns={"Date": "date", "Close": "close"})
        path.parent.mkdir(parents=True, exist_ok=True)
        hist.to_csv(path, index=False, encoding="utf-8")
        return hist
    except Exception:
        if path.exists():
            return pd.read_csv(path, parse_dates=["date"])
        return pd.DataFrame(columns=["date", "close"])


def compute_regression_beta(
    ticker: str, *, lookback_years: int = BETA_LOOKBACK_YEARS
) -> tuple[float | None, int]:
    """Local OLS beta: weekly returns of `ticker` (from cached `prices.csv`) vs. Ibovespa.

    Returns `(beta, n_weekly_observations)`. `beta` is `None` when there is
    not enough overlapping price history (< 52 weekly points) to trust the
    slope — callers should fall back to a peer-average or neutral beta.
    """
    prices_path = company_dir(ticker) / "financials" / "prices.csv"
    if not prices_path.exists():
        return None, 0
    try:
        px = pd.read_csv(prices_path)
    except (OSError, pd.errors.ParserError):
        return None, 0
    if px.empty:
        return None, 0

    date_col = "date" if "date" in px.columns else None
    close_col = "close" if "close" in px.columns else ("adjustedClose" if "adjustedClose" in px.columns else None)
    if date_col is None or close_col is None:
        return None, 0

    # `date` is unix seconds (brapi) or an ISO/date string (yfinance) depending on the sync source
    if pd.api.types.is_numeric_dtype(px[date_col]):
        px["_date"] = pd.to_datetime(px[date_col], unit="s", utc=True, errors="coerce")
    else:
        px["_date"] = pd.to_datetime(px[date_col], utc=True, errors="coerce")
    px = px.dropna(subset=["_date"]).sort_values("_date")
    if px.empty:
        return None, 0

    cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=lookback_years)
    px = px[px["_date"] >= cutoff]
    if px.empty:
        return None, 0

    stock_ret = px.set_index("_date")[close_col].resample("W-FRI").last().dropna().pct_change().dropna()

    idx = fetch_index_history()
    if idx.empty:
        return None, 0
    idx = idx.copy()
    idx["date"] = pd.to_datetime(idx["date"], utc=True, errors="coerce")
    idx = idx.dropna(subset=["date"]).set_index("date")["close"]
    idx = idx[idx.index >= cutoff]
    idx_ret = idx.resample("W-FRI").last().dropna().pct_change().dropna()

    joined = pd.concat({"stock": stock_ret, "index": idx_ret}, axis=1).dropna()
    if len(joined) < 52:
        return None, len(joined)

    var = joined["index"].var()
    if not var:
        return None, len(joined)
    cov = joined["index"].cov(joined["stock"])
    return float(cov / var), len(joined)
