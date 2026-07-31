from __future__ import annotations

import base64
import json
from typing import Any

from decifra.http_util import client, normalize_cnpj, normalize_ticker


def _b64(payload: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def _search_companies(query: str) -> list[dict[str, Any]]:
    payload = {
        "language": "pt-br",
        "pageNumber": 1,
        "pageSize": 20,
        "company": query,
    }
    url = (
        "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/"
        f"CompanyCall/GetInitialCompanies/{_b64(payload)}"
    )
    try:
        with client() as c:
            resp = c.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    if isinstance(data, list):
        return data
    return list(data.get("results") or [])


def _pick_result(ticker: str, stock_name: str, results: list[dict[str, Any]]) -> dict[str, Any] | None:
    t = normalize_ticker(ticker)
    stem = "".join(ch for ch in t if ch.isalpha())
    stock_u = (stock_name or "").strip().upper()

    # 1) Exact issuingCompany == ticker stem (PETR for PETR4)
    for item in results:
        issuing = str(item.get("issuingCompany") or "").upper()
        if issuing and issuing == stem:
            return item

    # 2) Exact tradingName / companyName match to B3 asset name
    for item in results:
        trading = str(item.get("tradingName") or "").upper()
        company = str(item.get("companyName") or "").upper()
        if stock_u and (trading == stock_u or stock_u in company or company.startswith(stock_u)):
            return item

    # 3) Single unambiguous result
    if len(results) == 1:
        return results[0]
    return None


def lookup_cnpj_by_ticker(ticker: str, stock_name: str = "") -> dict[str, str]:
    """Resolve CNPJ / company metadata from B3 listed companies search."""
    t = normalize_ticker(ticker)
    stock_name = (stock_name or "").strip()

    # Prefer precise queries first (full ticker, then stock name, then stem)
    stem = "".join(ch for ch in t if ch.isalpha())
    queries = []
    for q in (t, stock_name, stem):
        if q and q not in queries:
            queries.append(q)

    best: dict[str, Any] | None = None
    for q in queries:
        results = _search_companies(q)
        picked = _pick_result(t, stock_name, results)
        if picked:
            best = picked
            break

    if not best:
        return {}

    cnpj = normalize_cnpj(best.get("cnpj") or best.get("cnpjCompany"))
    website = str(best.get("website") or "")
    return {
        "cnpj": cnpj,
        "cvm_code": str(best.get("codeCVM") or ""),
        "company_name": str(best.get("companyName") or best.get("tradingName") or ""),
        "ri_url": website if website.startswith("http") else (f"https://{website}" if website else ""),
        "sector": str(best.get("sector") or best.get("segment") or ""),
        "issuing_company": str(best.get("issuingCompany") or ""),
    }


def enrich_constituents_with_b3(constituents: list[dict[str, Any]], *, force: bool = False) -> list[dict[str, Any]]:
    for c in constituents:
        if c.get("cnpj") and c.get("issuing_company") and not force:
            # Re-validate issuing_company matches ticker stem when present
            stem = "".join(ch for ch in c["ticker"] if ch.isalpha())
            if str(c.get("issuing_company", "")).upper() == stem.upper():
                continue
        if c.get("cnpj") and not force:
            stem = "".join(ch for ch in c["ticker"] if ch.isalpha())
            # If company_name clearly mismatches stock_name, refresh
            stock = (c.get("stock_name") or "").upper()
            company = (c.get("company_name") or "").upper()
            if stock and company and (stock in company or company.startswith(stock[:8])):
                continue
        info = lookup_cnpj_by_ticker(c["ticker"], c.get("stock_name") or "")
        if not info:
            continue
        for k, v in info.items():
            if v:
                c[k] = v
    return constituents
