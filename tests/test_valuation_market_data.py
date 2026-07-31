from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from decifra.valuation.market_data import compute_regression_beta, fetch_market_data


@pytest.fixture
def company_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("decifra.valuation.market_data.company_dir", lambda t: tmp_path / t.upper())
    return tmp_path / "AAA3"


def test_fetch_market_data_caches_result(company_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake_quote(ticker: str) -> dict:
        calls["n"] += 1
        return {
            "price": 25.0,
            "shares_outstanding": 1_000_000.0,
            "market_cap": 25_000_000.0,
            "beta": 1.2,
            "source": "yfinance",
        }

    monkeypatch.setattr("decifra.valuation.market_data._fetch_yfinance_quote", fake_quote)

    first = fetch_market_data("AAA3")
    assert first["price"] == 25.0
    assert first["stale"] is False
    assert calls["n"] == 1

    cache_path = company_root / "financials" / "market_data.json"
    assert cache_path.exists()
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cached["price"] == 25.0

    # Second call within cache window should not re-fetch
    second = fetch_market_data("AAA3")
    assert second["price"] == 25.0
    assert calls["n"] == 1

    # force=True bypasses the cache
    fetch_market_data("AAA3", force=True)
    assert calls["n"] == 2


def test_fetch_market_data_handles_provider_failure(
    company_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing_quote(ticker: str) -> dict:
        raise RuntimeError("no network")

    monkeypatch.setattr("decifra.valuation.market_data._fetch_yfinance_quote", failing_quote)
    data = fetch_market_data("AAA3")
    assert data["price"] is None
    assert data["stale"] is True
    assert data["source"] == "unavailable"


def test_compute_regression_beta_recovers_known_slope(
    company_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    n = 130
    t = np.arange(n)
    index_returns = 0.01 * np.sin(t * 0.3)
    stock_returns = 1.3 * index_returns  # exact linear relationship -> beta == 1.3

    index_prices = 100.0 * np.cumprod(1 + index_returns)
    stock_prices = 50.0 * np.cumprod(1 + stock_returns)
    dates = pd.date_range("2022-01-07", periods=n, freq="W-FRI")

    prices_path = company_root / "financials" / "prices.csv"
    prices_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"date": [int(d.timestamp()) for d in dates], "close": stock_prices}
    ).to_csv(prices_path, index=False)

    index_df = pd.DataFrame({"date": dates, "close": index_prices})
    monkeypatch.setattr("decifra.valuation.market_data.fetch_index_history", lambda **kw: index_df)

    beta, n_obs = compute_regression_beta("AAA3", lookback_years=5)
    assert n_obs >= 52
    assert beta == pytest.approx(1.3, abs=1e-6)


def test_compute_regression_beta_insufficient_history(
    company_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    beta, n_obs = compute_regression_beta("AAA3")
    assert beta is None
    assert n_obs == 0
