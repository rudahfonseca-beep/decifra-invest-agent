from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from decifra.config import COMPANIES_DIR, EQUITIES_JSON, IBOVESPA_JSON, ensure_dirs
from decifra.http_util import normalize_ticker

TickerScope = Literal["all", "core"]


def company_dir(ticker: str) -> Path:
    return COMPANIES_DIR / normalize_ticker(ticker)


def ensure_company_tree(ticker: str) -> Path:
    ensure_dirs()
    root = company_dir(ticker)
    for sub in (
        root / "financials",
        root / "debt",
        root / "fre",
        root / "notices" / "pdfs",
        root / "transcripts" / "pdfs",
        root / "transcripts" / "text",
    ):
        sub.mkdir(parents=True, exist_ok=True)
    return root


def meta_path(ticker: str) -> Path:
    return company_dir(ticker) / "meta.json"


def load_meta(ticker: str) -> dict[str, Any]:
    path = meta_path(ticker)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_identity(ticker: str) -> dict[str, Any]:
    """Company meta enriched via entity resolver (ISIN / multi-ticker) when available."""
    meta = load_meta(ticker)
    try:
        from decifra.entities.resolve import resolve_entity

        ent = resolve_entity(ticker=ticker)
        if not ent:
            return meta
        return {
            **meta,
            "cnpj": ent.get("cnpj") or meta.get("cnpj"),
            "cvm_code": ent.get("cvm_code") or meta.get("cvm_code"),
            "isins": ent.get("isins") or meta.get("isins") or [],
            "entity_tickers": ent.get("tickers") or [normalize_ticker(ticker)],
            "entity_sources": ent.get("sources") or [],
        }
    except Exception:
        return meta


def save_meta(ticker: str, meta: dict[str, Any]) -> Path:
    ensure_company_tree(ticker)
    meta = {**meta, "ticker": normalize_ticker(ticker)}
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = meta_path(ticker)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_universe() -> dict[str, Any]:
    """Load canonical equities universe; fall back to legacy ibovespa.json."""
    if EQUITIES_JSON.exists():
        return json.loads(EQUITIES_JSON.read_text(encoding="utf-8"))
    if IBOVESPA_JSON.exists():
        data = json.loads(IBOVESPA_JSON.read_text(encoding="utf-8"))
        # Legacy IBOV-only file: treat every constituent as core.
        for c in data.get("constituents", []):
            c.setdefault("indexes", ["IBOV"])
            c.setdefault("sync_tier", "core")
            c.setdefault("source", "ibovespa")
        return data
    return {"constituents": [], "count": 0}


def _is_core(constituent: dict[str, Any]) -> bool:
    if constituent.get("sync_tier") == "core":
        return True
    indexes = constituent.get("indexes") or []
    return "IBOV" in indexes


def list_tickers(
    ticker: str | None = None,
    *,
    scope: TickerScope = "all",
) -> list[str]:
    """List universe tickers.

    ``scope='all'`` — every listed equity in equities.json (or legacy IBOV).
    ``scope='core'`` — IBOV ∪ live ``watchlist.json`` ∪ constituents with ``sync_tier=core``.
    """
    if ticker:
        return [normalize_ticker(ticker)]
    data = load_universe()
    constituents = data.get("constituents", [])
    out: list[str] = []
    seen: set[str] = set()
    universe_set: set[str] = set()
    for c in constituents:
        t = normalize_ticker(c.get("ticker") or "")
        if not t:
            continue
        universe_set.add(t)
        if scope == "core" and not _is_core(c):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)

    if scope == "core":
        # Live watchlist elevates tickers without re-running sync universe.
        try:
            from decifra.universe.listed import load_watchlist

            for t in load_watchlist():
                if not t or t in seen:
                    continue
                if t in universe_set or meta_path(t).exists():
                    seen.add(t)
                    out.append(t)
        except Exception:
            pass
    return out
