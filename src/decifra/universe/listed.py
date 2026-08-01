"""Full B3 listed-equity universe (tiered: index vs core)."""

from __future__ import annotations

import base64
import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from decifra.config import (
    B3_COMPANY_DETAIL_URL,
    B3_LISTED_COMPANIES_URL,
    DOWNLOAD_SLEEP_S,
    EQUITIES_JSON,
    IBOVESPA_JSON,
    WATCHLIST_JSON,
    ensure_dirs,
)
from decifra.http_util import client, normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, save_meta
from decifra.universe.ibovespa import (
    _enrich_from_cadastro,
    _fill_cnpj_from_known_patterns,
    download_cadastro,
    sync_universe as sync_ibovespa_universe,
)

# B3 equity tickers: 4 letters + 1–2 digits (PETR4, SANB11). Exclude bonds (PETR-DEB…).
_EQUITY_CODE_RE = re.compile(r"^[A-Z]{4}\d{1,2}$")


def _b64(payload: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def is_equity_ticker(code: str) -> bool:
    t = normalize_ticker(code)
    return bool(t and _EQUITY_CODE_RE.match(t) and "-" not in code)


def load_watchlist(path=None) -> list[str]:
    """Return normalized tickers from watchlist.json (list or {tickers: [...]})."""
    p = path or WATCHLIST_JSON
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = raw.get("tickers") or raw.get("constituents") or []
    else:
        return []
    out: list[str] = []
    for item in items:
        if isinstance(item, str):
            t = normalize_ticker(item)
        elif isinstance(item, dict):
            t = normalize_ticker(item.get("ticker") or "")
        else:
            continue
        if t and t not in out:
            out.append(t)
    return out


def fetch_listed_issuers(*, page_size: int = 120) -> list[dict[str, Any]]:
    """Paginate B3 GetInitialCompanies; keep active equity issuers (type=1)."""
    results: list[dict[str, Any]] = []
    page = 1
    with client() as c:
        while True:
            payload = {
                "language": "pt-br",
                "pageNumber": page,
                "pageSize": page_size,
                "company": "",
            }
            url = f"{B3_LISTED_COMPANIES_URL}{_b64(payload)}"
            resp = c.get(url)
            resp.raise_for_status()
            data = resp.json()
            for row in data.get("results") or []:
                if str(row.get("status") or "").upper() != "A":
                    continue
                # type "1" = listed company / equity issuer (vs funds, unclassified)
                if str(row.get("type") or "") != "1":
                    continue
                results.append(row)
            page_info = data.get("page") or {}
            total_pages = int(page_info.get("totalPages") or 1)
            if page >= total_pages:
                break
            page += 1
    return results


def fetch_company_detail(code_cvm: str) -> dict[str, Any]:
    """B3 GetDetail by CVM code — includes ``code`` / ``otherCodes`` tickers."""
    code = str(code_cvm or "").strip()
    if not code:
        return {}
    payload = {"codeCVM": code, "language": "pt-br"}
    url = f"{B3_COMPANY_DETAIL_URL}{_b64(payload)}"
    try:
        with client() as c:
            resp = c.get(url)
            if not resp.content:
                return {}
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def equity_codes_from_detail(detail: dict[str, Any]) -> list[dict[str, str]]:
    """Extract ON/PN/unit tickers (+ ISIN when present) from GetDetail."""
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(code: str, isin: str = "") -> None:
        if not is_equity_ticker(code):
            return
        t = normalize_ticker(code)
        if t in seen:
            return
        seen.add(t)
        found.append({"ticker": t, "isin": (isin or "").strip()})

    _add(str(detail.get("code") or ""))
    for item in detail.get("otherCodes") or []:
        if not isinstance(item, dict):
            continue
        _add(str(item.get("code") or ""), str(item.get("isin") or ""))
    return found


def _build_ibov_payload(force_cadastro: bool = False) -> dict[str, Any]:
    """Refresh Ibovespa snapshot (also used for core membership tags)."""
    return sync_ibovespa_universe(force_cadastro=force_cadastro)


def sync_listed_universe(
    *,
    force_cadastro: bool = False,
    fetch_details: bool = True,
    sleep_s: float | None = None,
) -> dict[str, Any]:
    """Build ``equities.json`` from all B3 listed issuers + IBOV/watchlist tiers."""
    ensure_dirs()
    sleep = DOWNLOAD_SLEEP_S if sleep_s is None else sleep_s

    ibov_payload = _build_ibov_payload(force_cadastro=force_cadastro)
    ibov_tickers = {
        normalize_ticker(c["ticker"])
        for c in ibov_payload.get("constituents", [])
        if c.get("ticker")
    }
    watch = set(load_watchlist())
    core_set = ibov_tickers | watch

    cad = download_cadastro(force=force_cadastro)
    issuers = fetch_listed_issuers()

    constituents: list[dict[str, Any]] = []
    seen_tickers: set[str] = set()

    for issuer in issuers:
        code_cvm = str(issuer.get("codeCVM") or "").strip()
        issuing = str(issuer.get("issuingCompany") or "").strip().upper()
        trading = str(issuer.get("tradingName") or "").strip()
        company = str(issuer.get("companyName") or "").strip()
        cnpj = normalize_cnpj(issuer.get("cnpj"))
        sector = str(issuer.get("segment") or "").strip()

        enrich = _enrich_from_cadastro(cad, trading or company)
        if enrich.get("cnpj") and not cnpj:
            cnpj = enrich["cnpj"]
        cvm_code = code_cvm or str(enrich.get("cvm_code") or "")
        company_name = enrich.get("company_name") or company
        ri_url = enrich.get("ri_url") or ""
        if enrich.get("sector"):
            sector = enrich["sector"]

        tickers_meta: list[dict[str, str]] = []
        if fetch_details and code_cvm:
            detail = fetch_company_detail(code_cvm)
            if sleep:
                time.sleep(sleep)
            tickers_meta = equity_codes_from_detail(detail)
            if detail.get("website") and not ri_url:
                site = str(detail.get("website") or "")
                ri_url = site if site.startswith("http") else (f"https://{site}" if site else "")
            if detail.get("companyName"):
                company_name = str(detail.get("companyName") or company_name)
            if not cnpj:
                cnpj = normalize_cnpj(detail.get("cnpj"))

        if not tickers_meta and issuing:
            # Fallback: no detail — skip issuer (avoid inventing suffixes)
            continue

        for tm in tickers_meta:
            t = tm["ticker"]
            if t in seen_tickers:
                continue
            seen_tickers.add(t)
            indexes: list[str] = []
            if t in ibov_tickers:
                indexes.append("IBOV")
            sync_tier = "core" if t in core_set else "index"
            entry = {
                "ticker": t,
                "stock_name": trading,
                "type": "",
                "isin": tm.get("isin") or "",
                "cnpj": cnpj,
                "cvm_code": cvm_code,
                "company_name": company_name,
                "ri_url": ri_url,
                "sector": sector,
                "issuing_company": issuing,
                "indexes": indexes,
                "sync_tier": sync_tier,
                "source": "b3_listed",
            }
            constituents.append(entry)

    # Ensure IBOV constituents exist even if detail filter missed them
    ibov_by_t = {
        normalize_ticker(c["ticker"]): c for c in ibov_payload.get("constituents", []) if c.get("ticker")
    }
    for t, c in ibov_by_t.items():
        if t in seen_tickers:
            for e in constituents:
                if e["ticker"] == t:
                    e["indexes"] = sorted(set(e.get("indexes") or []) | {"IBOV"})
                    e["sync_tier"] = "core"
                    e["part_pct"] = c.get("part_pct")
                    e["type"] = c.get("type") or e.get("type")
                    if c.get("cnpj") and not e.get("cnpj"):
                        e["cnpj"] = c["cnpj"]
                    break
            continue
        seen_tickers.add(t)
        constituents.append(
            {
                "ticker": t,
                "stock_name": c.get("stock_name"),
                "type": c.get("type") or "",
                "isin": "",
                "cnpj": c.get("cnpj", ""),
                "cvm_code": c.get("cvm_code", ""),
                "company_name": c.get("company_name", ""),
                "ri_url": c.get("ri_url", ""),
                "sector": c.get("sector", ""),
                "issuing_company": "".join(ch for ch in t if ch.isalpha()),
                "part_pct": c.get("part_pct"),
                "indexes": ["IBOV"],
                "sync_tier": "core",
                "source": "ibovespa",
            }
        )

    # Watchlist-only names (not yet in listed fetch)
    for t in sorted(watch):
        if t in seen_tickers:
            for e in constituents:
                if e["ticker"] == t:
                    e["sync_tier"] = "core"
                    break
            continue
        seen_tickers.add(t)
        constituents.append(
            {
                "ticker": t,
                "stock_name": t,
                "type": "",
                "isin": "",
                "cnpj": "",
                "cvm_code": "",
                "company_name": "",
                "ri_url": "",
                "sector": "",
                "issuing_company": "".join(ch for ch in t if ch.isalpha()),
                "indexes": [],
                "sync_tier": "core",
                "source": "watchlist",
            }
        )

    constituents = _fill_cnpj_from_known_patterns(constituents, cad)
    constituents.sort(key=lambda c: c["ticker"])

    payload = {
        "index": "B3_LISTED",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(constituents),
        "core_count": sum(1 for c in constituents if c.get("sync_tier") == "core"),
        "ibov_count": sum(1 for c in constituents if "IBOV" in (c.get("indexes") or [])),
        "constituents": constituents,
    }
    EQUITIES_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for c in constituents:
        ensure_company_tree(c["ticker"])
        save_meta(
            c["ticker"],
            {
                "ticker": c["ticker"],
                "stock_name": c.get("stock_name"),
                "type": c.get("type"),
                "isin": c.get("isin", ""),
                "cnpj": c.get("cnpj", ""),
                "cvm_code": c.get("cvm_code", ""),
                "company_name": c.get("company_name", ""),
                "ri_url": c.get("ri_url", ""),
                "sector": c.get("sector", ""),
                "part_pct": c.get("part_pct"),
                "issuing_company": c.get("issuing_company", ""),
                "indexes": c.get("indexes") or [],
                "sync_tier": c.get("sync_tier") or "index",
                "source": c.get("source") or "b3_listed",
            },
        )

    return payload


def sync_universe(force_cadastro: bool = False, *, fetch_details: bool = True) -> dict[str, Any]:
    """CLI entry: full listed equities + refreshed Ibovespa snapshot."""
    return sync_listed_universe(force_cadastro=force_cadastro, fetch_details=fetch_details)
