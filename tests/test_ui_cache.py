"""UI / lake-API cache behavior (dual credit DF + screener TTL)."""

from __future__ import annotations

import pandas as pd

from decifra.schemas import ui_cache
from decifra.schemas.api_server import handle_api
from decifra.schemas.research_api import get_credit_df
from decifra.schemas.screener import assemble_opportunity_screener


def setup_function() -> None:
    ui_cache.clear_all_ui_caches()


def test_dual_credit_cache_keeps_both_modes(monkeypatch):
    calls: list[bool] = []

    def fake_build(*, include_signals: bool = False, tickers=None):
        calls.append(include_signals)
        return pd.DataFrame({"ticker": ["PETR4"], "has_financials": [True], "sig": [include_signals]})

    monkeypatch.setattr("decifra.schemas.research_api.build_credit_table", fake_build)

    fund = get_credit_df(include_signals=False)
    sig = get_credit_df(include_signals=True)
    assert calls == [False, True]
    assert get_credit_df(include_signals=False) is fund
    assert get_credit_df(include_signals=True) is sig
    assert calls == [False, True]  # cache hits, no rebuild


def test_api_defaults_signals_off(monkeypatch):
    def fake_build(*, include_signals: bool = False, tickers=None):
        return pd.DataFrame(
            {
                "ticker": ["PETR4"],
                "company": ["Petrobras"],
                "cnpj": [""],
                "isins": [[]],
                "industry_group": ["Energy"],
                "sector": ["Energy"],
                "cohort": ["non_financial"],
                "period": ["2024"],
                "has_financials": [True],
                "credit_score": [70.0],
                "fundamental_score": [70.0],
                "qualitative_penalty": [0.0],
                "peer_benchmark": [True],
                "debt_to_equity": [1.0],
                "current_ratio": [1.2],
                "interest_coverage": [5.0],
                "net_margin": [0.1],
                "equity_to_assets": [0.4],
                "roe": [0.15],
                "signal_hits": [""],
            }
        )

    monkeypatch.setattr("decifra.schemas.research_api.build_credit_table", fake_build)
    ui_cache.clear_credit_cache()

    code, payload = handle_api("/api/credit", {})
    assert code == 200
    assert payload["filters"]["include_signals"] is False

    code, ind = handle_api("/api/industries", {})
    assert code == 200
    assert len(ind["industries"]) >= 1


def test_screener_ttl_cache_reuse(monkeypatch):
    n = {"calls": 0}

    def fake_row(ticker: str):
        n["calls"] += 1
        return {
            "ticker": ticker,
            "cnpj": "",
            "isin": "",
            "company_name": ticker,
            "apv_discount_pct": 1.0,
            "ev_equity": 1.0,
            "net_debt_ebitda": 1.0,
            "dscr": 2.0,
            "merton_pd_pct": 0.5,
            "signal": "safe",
            "lineage": {"equity": "test", "credit": "test"},
        }

    monkeypatch.setattr(
        "decifra.schemas.screener.list_tickers", lambda: ["PETR4", "VALE3", "ITUB4"]
    )
    monkeypatch.setattr("decifra.schemas.screener.assemble_screener_row", fake_row)

    first = assemble_opportunity_screener(limit=2)
    second = assemble_opportunity_screener(limit=2)
    assert first is second
    assert n["calls"] == 2
    third = assemble_opportunity_screener(limit=2, refresh=True)
    assert third is not first
    assert n["calls"] == 4
    assert len(third["rows"]) == 2


def test_ttl_helpers():
    ui_cache.ttl_set("k", {"v": 1}, ttl_seconds=60)
    assert ui_cache.ttl_get("k") == {"v": 1}
    assert ui_cache.ttl_get_or_set("k", lambda: {"v": 2}) == {"v": 1}
