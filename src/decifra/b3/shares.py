"""B3 share counts / market cap artifact (prefer over yfinance-only)."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any

from decifra.config import B3_SHARES_JSON, ensure_dirs
from decifra.http_util import client, normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, list_tickers, load_meta, load_universe, save_meta

# B3 listed companies — GetDetail is identity-only; share counts live on Supplement.
B3_LISTED_URL = (
    "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetDetail/"
)
B3_SUPPLEMENT_URL = (
    "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/"
    "CompanyCall/GetListedSupplementCompany/"
)


def _b64(payload: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def _load_existing() -> dict[str, Any]:
    if B3_SHARES_JSON.exists():
        return json.loads(B3_SHARES_JSON.read_text(encoding="utf-8"))
    return {"updated_at": None, "shares": []}


def _pick_number(data: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        val = data.get(key)
        if val in (None, "", 0, "0"):
            continue
        try:
            # B3 sometimes returns Brazilian thousands separators
            if isinstance(val, str):
                cleaned = val.replace(".", "").replace(",", ".")
                num = float(cleaned)
            else:
                num = float(val)
            if num > 0:
                return num
        except (TypeError, ValueError):
            continue
    return None


def fetch_b3_share_detail(
    *,
    cvm_code: str | None = None,
    issuing_company: str | None = None,
) -> dict[str, Any]:
    """Call B3 GetListedSupplementCompany for ON/PN/total share counts.

    ``GetDetail`` is identity-only (no share fields). Supplement returns
    ``numberCommonShares`` / ``numberPreferredShares`` / ``totalNumberShares``.
    """
    payloads: list[dict[str, Any]] = []
    if issuing_company:
        payloads.append({"issuingCompany": str(issuing_company).upper().strip(), "language": "pt-br"})
    if cvm_code:
        payloads.append({"codeCVM": str(cvm_code), "language": "pt-br"})
    if not payloads:
        return {}

    for payload in payloads:
        url = f"{B3_SUPPLEMENT_URL}{_b64(payload)}"
        try:
            with client() as c:
                resp = c.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            continue
        rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        for row in rows:
            if not isinstance(row, dict):
                continue
            # Prefer matching CVM code when multiple supplements return
            if cvm_code and str(row.get("codeCVM") or "") not in ("", str(cvm_code)):
                continue
            total = _pick_number(row, ("totalNumberShares", "totalShares", "sharesOutstanding"))
            on = _pick_number(row, ("numberCommonShares",))
            pn = _pick_number(row, ("numberPreferredShares",))
            if total is None and (on is not None or pn is not None):
                total = (on or 0.0) + (pn or 0.0)
            if total:
                return {
                    "shares_outstanding": int(total),
                    "number_common": int(on) if on else None,
                    "number_preferred": int(pn) if pn else None,
                    "stock_capital": row.get("stockCapital"),
                    "source": "B3_GetListedSupplementCompany",
                }
    return {}


def sync_b3_shares(
    *,
    ticker: str | None = None,
    force: bool = False,
    use_network: bool = False,
) -> dict[str, Any]:
    """Build ``data/universe/b3_shares.json`` from universe meta (+ optional live B3).

    When ``use_network`` is False (default), derives a research artifact from
    local meta / Ibovespa part_pct without hitting B3 detail endpoints.
    """
    ensure_dirs()
    existing = _load_existing()
    by_ticker = {
        normalize_ticker(r["ticker"]): r for r in existing.get("shares", []) if r.get("ticker")
    }

    tickers = list_tickers(ticker)
    universe = load_universe()
    part_by_t = {
        normalize_ticker(c["ticker"]): c for c in universe.get("constituents", [])
    }
    updated: list[str] = []
    network_hits = 0

    for t in tickers:
        meta = load_meta(t)
        row = by_ticker.get(t, {})
        shares_out = int(row.get("shares_outstanding") or 0)
        mcap = row.get("market_cap_brl")
        source = row.get("source", "local_meta")

        if use_network and (force or not shares_out):
            uc = part_by_t.get(t, {})
            detail = fetch_b3_share_detail(
                cvm_code=str(meta.get("cvm_code") or uc.get("cvm_code") or "") or None,
                issuing_company=str(
                    meta.get("issuing_company")
                    or uc.get("issuing_company")
                    or "".join(ch for ch in t if ch.isalpha())
                )
                or None,
            )
            if detail.get("shares_outstanding"):
                shares_out = int(detail["shares_outstanding"])
                source = detail.get("source", "B3_GetDetail")
                network_hits += 1
            if detail.get("market_cap_brl") is not None:
                mcap = detail["market_cap_brl"]
            elif not shares_out:
                source = "B3_pending_network"

        uc = part_by_t.get(t, {})
        rec = {
            "ticker": t,
            "cnpj": normalize_cnpj(meta.get("cnpj") or uc.get("cnpj")),
            "shares_outstanding": shares_out or None,
            "market_cap_brl": mcap,
            "part_pct": uc.get("part_pct"),
            "source": source,
            "lineage": {"source_doc": "b3_shares.json"},
        }
        by_ticker[t] = rec
        ensure_company_tree(t)
        company_path = ensure_company_tree(t) / "financials" / "b3_shares.json"
        company_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        if meta:
            meta["shares_outstanding"] = rec["shares_outstanding"]
            meta["b3_shares_source"] = source
            save_meta(t, meta)
        updated.append(t)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "shares": sorted(by_ticker.values(), key=lambda r: r["ticker"]),
    }
    B3_SHARES_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "tickers": len(tickers),
        "updated": updated,
        "network_hits": network_hits,
        "path": str(B3_SHARES_JSON),
    }
