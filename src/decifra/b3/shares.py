"""B3 share counts / market cap artifact (prefer over yfinance-only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decifra.config import B3_SHARES_JSON, ensure_dirs
from decifra.http_util import normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, list_tickers, load_meta, load_universe, save_meta

# B3 listed companies detail (same family as CNPJ enrich)
B3_LISTED_URL = (
    "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetDetail/"
)


def _load_existing() -> dict[str, Any]:
    if B3_SHARES_JSON.exists():
        return json.loads(B3_SHARES_JSON.read_text(encoding="utf-8"))
    return {"updated_at": None, "shares": []}


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

    for t in tickers:
        meta = load_meta(t)
        row = by_ticker.get(t, {})
        if row and not force and t != (ticker or "").upper():
            # keep cached unless force / single-ticker refresh
            pass
        shares_out = int(row.get("shares_outstanding") or 0)
        mcap = row.get("market_cap_brl")
        source = row.get("source", "local_meta")

        if use_network and not shares_out:
            # Reserved for official B3 detail API; keep artifact path stable.
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
    return {"tickers": len(tickers), "updated": updated, "path": str(B3_SHARES_JSON)}
