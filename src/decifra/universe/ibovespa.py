from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from decifra.config import (
    B3_IBOV_PORTFOLIO_URL,
    CADASTRO_CSV,
    CVM_CADASTRO_URL,
    IBOVESPA_JSON,
    ensure_dirs,
)
from decifra.http_util import client, download_to_file, normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, save_meta


def _b3_payload(page_number: int = 1, page_size: int = 120) -> str:
    payload = {
        "language": "pt-br",
        "pageNumber": page_number,
        "pageSize": page_size,
        "index": "IBOV",
        "segment": "1",
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def fetch_ibovespa_raw() -> list[dict[str, Any]]:
    """Fetch current Ibovespa theoretical portfolio from B3 Listados."""
    results: list[dict[str, Any]] = []
    page = 1
    with client() as c:
        while True:
            url = f"{B3_IBOV_PORTFOLIO_URL}{_b3_payload(page)}"
            resp = c.get(url)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("results") or [])
            page_info = data.get("page") or {}
            total_pages = int(page_info.get("totalPages") or 1)
            if page >= total_pages:
                break
            page += 1
    return results


def download_cadastro(force: bool = False) -> pd.DataFrame:
    ensure_dirs()
    download_to_file(CVM_CADASTRO_URL, CADASTRO_CSV, force=force)
    df = pd.read_csv(CADASTRO_CSV, sep=";", encoding="latin-1", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    if "CNPJ_CIA" in df.columns:
        df["CNPJ_NORM"] = df["CNPJ_CIA"].map(normalize_cnpj)
    return df


def _enrich_from_cadastro(cad: pd.DataFrame, stock_name: str) -> dict[str, Any]:
    name = (stock_name or "").strip().upper()
    if not name or "DENOM_CIA" not in cad.columns:
        return {}
    # Exact-ish commercial name match
    for col in ("DENOM_COMERC", "DENOM_CIA"):
        if col not in cad.columns:
            continue
        mask = cad[col].fillna("").str.upper().str.contains(name[:12], regex=False)
        hits = cad[mask]
        if len(hits) == 1:
            row = hits.iloc[0]
            return {
                "cnpj": normalize_cnpj(row.get("CNPJ_CIA")),
                "cvm_code": str(row.get("CD_CVM") or "").strip(),
                "company_name": str(row.get("DENOM_CIA") or "").strip(),
                "ri_url": str(row.get("LINK_SITE") or row.get("PAGINA_WEB") or "").strip(),
                "sector": str(row.get("SETOR_ATIV") or "").strip(),
            }
    # Fallback: startswith first token
    token = name.split()[0] if name else ""
    if token and "DENOM_COMERC" in cad.columns:
        mask = cad["DENOM_COMERC"].fillna("").str.upper().str.startswith(token)
        hits = cad[mask]
        if len(hits) >= 1:
            row = hits.iloc[0]
            return {
                "cnpj": normalize_cnpj(row.get("CNPJ_CIA")),
                "cvm_code": str(row.get("CD_CVM") or "").strip(),
                "company_name": str(row.get("DENOM_CIA") or "").strip(),
                "ri_url": str(row.get("LINK_SITE") or row.get("PAGINA_WEB") or "").strip(),
                "sector": str(row.get("SETOR_ATIV") or "").strip(),
            }
    return {}


def sync_universe(force_cadastro: bool = False) -> dict[str, Any]:
    ensure_dirs()
    raw = fetch_ibovespa_raw()
    cad = download_cadastro(force=force_cadastro)

    constituents: list[dict[str, Any]] = []
    for item in raw:
        ticker = normalize_ticker(item.get("cod") or item.get("code") or "")
        if not ticker or ticker in {"QUANTIDADE TEÓRICA TOTAL", "REDUCTO"}:
            continue
        # Skip aggregate footer rows
        if not any(ch.isdigit() for ch in ticker):
            continue
        stock = str(item.get("asset") or item.get("stock") or "").strip()
        enrich = _enrich_from_cadastro(cad, stock)
        entry = {
            "ticker": ticker,
            "stock_name": stock,
            "type": str(item.get("type") or item.get("spec") or "").strip(),
            "part_pct": item.get("part") or item.get("partPct"),
            "theoretical_qty": item.get("theoricalQty") or item.get("theoreticalQty"),
            **enrich,
        }
        constituents.append(entry)

    # Deduplicate by ticker keeping first
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for c in constituents:
        if c["ticker"] in seen:
            continue
        seen.add(c["ticker"])
        unique.append(c)

    # Second pass: join CNPJ via DFP company file if present in cache later is handled in financials.
    # Also try matching ticker prefix in DENOM_COMERC for banks etc via common mapping helpers.
    unique = _fill_cnpj_from_known_patterns(unique, cad)

    payload = {
        "index": "IBOV",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(unique),
        "constituents": unique,
    }
    IBOVESPA_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for c in unique:
        ensure_company_tree(c["ticker"])
        save_meta(
            c["ticker"],
            {
                "ticker": c["ticker"],
                "stock_name": c.get("stock_name"),
                "type": c.get("type"),
                "cnpj": c.get("cnpj", ""),
                "cvm_code": c.get("cvm_code", ""),
                "company_name": c.get("company_name", ""),
                "ri_url": c.get("ri_url", ""),
                "sector": c.get("sector", ""),
                "part_pct": c.get("part_pct"),
                "source": "ibovespa",
            },
        )

    return payload


def _fill_cnpj_from_known_patterns(
    constituents: list[dict[str, Any]], cad: pd.DataFrame
) -> list[dict[str, Any]]:
    """Improve CNPJ coverage using ticker stem vs commercial name heuristics."""
    if cad.empty or "DENOM_COMERC" not in cad.columns:
        return constituents

    # Map of common Ibovespa name tokens used by B3 asset field → cadastro search
    for c in constituents:
        if c.get("cnpj"):
            continue
        stock = (c.get("stock_name") or "").upper()
        ticker = c["ticker"]
        stem = "".join(ch for ch in ticker if ch.isalpha())
        search_terms = [stock, stem]
        for term in search_terms:
            term = term.strip()
            if len(term) < 3:
                continue
            mask = cad["DENOM_COMERC"].fillna("").str.upper().str.contains(term[:10], regex=False)
            hits = cad[mask]
            if "SIT" in hits.columns:
                active = hits[hits["SIT"].str.contains("ATIVO", case=False, na=False)]
                if not active.empty:
                    hits = active
            if len(hits) == 1:
                row = hits.iloc[0]
                c["cnpj"] = normalize_cnpj(row.get("CNPJ_CIA"))
                c["cvm_code"] = str(row.get("CD_CVM") or "").strip()
                c["company_name"] = str(row.get("DENOM_CIA") or "").strip()
                c["ri_url"] = str(row.get("LINK_SITE") or row.get("PAGINA_WEB") or "").strip()
                c["sector"] = str(row.get("SETOR_ATIV") or "").strip()
                break
    return constituents


def attach_cnpj_map(cnpj_by_ticker: dict[str, str]) -> None:
    """Update universe + meta with CNPJ map discovered from financial files."""
    if not IBOVESPA_JSON.exists():
        return
    data = json.loads(IBOVESPA_JSON.read_text(encoding="utf-8"))
    for c in data.get("constituents", []):
        t = c["ticker"]
        if t in cnpj_by_ticker and not c.get("cnpj"):
            c["cnpj"] = cnpj_by_ticker[t]
    IBOVESPA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    for t, cnpj in cnpj_by_ticker.items():
        meta_path = ensure_company_tree(t) / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["cnpj"] = cnpj
            save_meta(t, meta)
