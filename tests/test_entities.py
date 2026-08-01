"""Phase 2 entity resolution tests."""

from __future__ import annotations

import json

from decifra.entities.resolve import (
    HIERARCHY_OF_TRUTH,
    prefer_source,
    resolve_conflict,
    resolve_entity,
    save_entities,
)


def test_hierarchy_order():
    assert HIERARCHY_OF_TRUTH[0] == "CVM"
    assert prefer_source("ANBIMA", "CVM") == "CVM"
    assert prefer_source("WEB_SCREENER", "RATING_AGENCY") == "RATING_AGENCY"
    winner = resolve_conflict(
        [
            {"value": 1, "source": "WEB_SCREENER"},
            {"value": 2, "source": "CVM"},
            {"value": 3, "source": "ANBIMA"},
        ]
    )
    assert winner is not None
    assert winner["value"] == 2


def test_resolve_from_entities_file(tmp_path, monkeypatch):
    import decifra.entities.resolve as resolve_mod

    payload = {
        "entities": [
            {
                "cnpj": "33000167000101",
                "cvm_code": "9512",
                "tickers": ["PETR4", "PETR3"],
                "isins": ["BRPETRDBS0A1"],
                "company_name": "PETROBRAS",
                "category_a": True,
                "sources": ["B3", "ANBIMA"],
            }
        ]
    }
    path = tmp_path / "entities.json"
    save_entities(payload, path)
    monkeypatch.setattr(resolve_mod, "ENTITIES_JSON", path)
    # entities_path uses ENTITIES_JSON from config — patch load via path arg
    data = json.loads(path.read_text(encoding="utf-8"))
    ent = resolve_entity(ticker="PETR4", entities=data)
    assert ent is not None
    assert ent["cnpj"] == "33000167000101"
    ent2 = resolve_entity(isin="BRPETRDBS0A1", entities=data)
    assert ent2 is not None
    assert "PETR3" in ent2["tickers"]
