from __future__ import annotations

from decifra.universe.b3_cnpj import _pick_result


def test_pick_prefers_issuing_company_stem():
    results = [
        {"issuingCompany": "ACPE", "tradingName": "ACU PETROLEO", "companyName": "ACU"},
        {"issuingCompany": "PETR", "tradingName": "PETROBRAS", "companyName": "PETROLEO BRASILEIRO"},
    ]
    picked = _pick_result("PETR4", "PETROBRAS", results)
    assert picked is not None
    assert picked["issuingCompany"] == "PETR"
