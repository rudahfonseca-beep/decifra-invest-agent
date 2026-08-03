from __future__ import annotations

import json
from pathlib import Path

from decifra.store.folders import list_tickers, load_universe
from decifra.universe.listed import (
    equity_codes_from_detail,
    is_equity_ticker,
    load_watchlist,
)


def test_is_equity_ticker():
    assert is_equity_ticker("PETR4")
    assert is_equity_ticker("SANB11")
    assert not is_equity_ticker("PETR-DEB62")
    assert not is_equity_ticker("QUANTIDADE")
    assert not is_equity_ticker("PETR")


def test_equity_codes_from_detail():
    detail = {
        "code": "PETR4",
        "otherCodes": [
            {"code": "PETR3", "isin": "BRPETRACNOR9"},
            {"code": "PETR4", "isin": "BRPETRACNPR6"},
            {"code": "PETR-DEB62", "isin": "BRPETRDBS092"},
        ],
    }
    codes = equity_codes_from_detail(detail)
    tickers = {c["ticker"] for c in codes}
    assert tickers == {"PETR3", "PETR4"}
    by_t = {c["ticker"]: c for c in codes}
    assert by_t["PETR3"]["isin"] == "BRPETRACNOR9"


def test_load_watchlist_list(tmp_path: Path, monkeypatch):
    path = tmp_path / "watchlist.json"
    path.write_text(json.dumps(["vale3", "PETR4"]), encoding="utf-8")
    monkeypatch.setattr("decifra.universe.listed.WATCHLIST_JSON", path)
    assert load_watchlist() == ["VALE3", "PETR4"]


def test_list_tickers_scope(tmp_path: Path, monkeypatch):
    equities = {
        "index": "B3_LISTED",
        "constituents": [
            {"ticker": "PETR4", "sync_tier": "core", "indexes": ["IBOV"]},
            {"ticker": "ABCD3", "sync_tier": "index", "indexes": []},
            {"ticker": "WXYZ4", "sync_tier": "core", "indexes": []},
        ],
    }
    eq_path = tmp_path / "equities.json"
    eq_path.write_text(json.dumps(equities), encoding="utf-8")
    monkeypatch.setattr("decifra.store.folders.EQUITIES_JSON", eq_path)
    monkeypatch.setattr("decifra.store.folders.IBOVESPA_JSON", tmp_path / "missing.json")
    empty_wl = tmp_path / "watchlist.json"
    empty_wl.write_text(json.dumps([]), encoding="utf-8")
    monkeypatch.setattr("decifra.universe.listed.WATCHLIST_JSON", empty_wl)

    assert len(load_universe().get("constituents", [])) == 3
    assert list_tickers(scope="all") == ["PETR4", "ABCD3", "WXYZ4"]
    assert list_tickers(scope="core") == ["PETR4", "WXYZ4"]
    assert list_tickers("abcd3") == ["ABCD3"]


def test_list_tickers_core_includes_live_watchlist(tmp_path: Path, monkeypatch):
    equities = {
        "index": "B3_LISTED",
        "constituents": [
            {"ticker": "PETR4", "sync_tier": "core", "indexes": ["IBOV"]},
            {"ticker": "ALPA4", "sync_tier": "index", "indexes": []},
        ],
    }
    eq_path = tmp_path / "equities.json"
    eq_path.write_text(json.dumps(equities), encoding="utf-8")
    monkeypatch.setattr("decifra.store.folders.EQUITIES_JSON", eq_path)
    monkeypatch.setattr("decifra.store.folders.IBOVESPA_JSON", tmp_path / "missing.json")
    wl = tmp_path / "watchlist.json"
    wl.write_text(json.dumps(["ALPA4"]), encoding="utf-8")
    monkeypatch.setattr("decifra.universe.listed.WATCHLIST_JSON", wl)

    assert list_tickers(scope="core") == ["PETR4", "ALPA4"]


def test_load_universe_ibov_fallback(tmp_path: Path, monkeypatch):
    ibov = {
        "index": "IBOV",
        "constituents": [{"ticker": "VALE3", "company_name": "VALE"}],
    }
    ibov_path = tmp_path / "ibovespa.json"
    ibov_path.write_text(json.dumps(ibov), encoding="utf-8")
    monkeypatch.setattr("decifra.store.folders.EQUITIES_JSON", tmp_path / "no_equities.json")
    monkeypatch.setattr("decifra.store.folders.IBOVESPA_JSON", ibov_path)
    empty_wl = tmp_path / "watchlist.json"
    empty_wl.write_text(json.dumps([]), encoding="utf-8")
    monkeypatch.setattr("decifra.universe.listed.WATCHLIST_JSON", empty_wl)

    data = load_universe()
    assert data["constituents"][0]["sync_tier"] == "core"
    assert list_tickers(scope="core") == ["VALE3"]
