"""Entity resolution and Hierarchy of Truth."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decifra.config import ENTITIES_JSON, ensure_dirs
from decifra.http_util import normalize_cnpj, normalize_ticker
from decifra.store.folders import load_meta, load_universe

# Strict precedence when metric values conflict across sources.
HIERARCHY_OF_TRUTH = (
    "CVM",
    "ANBIMA",
    "RATING_AGENCY",
    "WEB_SCREENER",
)

SOURCE_RANK = {name: i for i, name in enumerate(HIERARCHY_OF_TRUTH)}


def entities_path() -> Path:
    ensure_dirs()
    return ENTITIES_JSON


def load_entities(path: Path | None = None) -> dict[str, Any]:
    p = path or entities_path()
    if not p.exists():
        return {"updated_at": None, "entities": [], "hierarchy": list(HIERARCHY_OF_TRUTH)}
    return json.loads(p.read_text(encoding="utf-8"))


def save_entities(payload: dict[str, Any], path: Path | None = None) -> Path:
    p = path or entities_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **payload,
        "hierarchy": list(HIERARCHY_OF_TRUTH),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def prefer_source(a: str, b: str) -> str:
    """Return the higher-ranked source name (lower rank index wins)."""
    ra = SOURCE_RANK.get(a.upper(), 99)
    rb = SOURCE_RANK.get(b.upper(), 99)
    return a if ra <= rb else b


def resolve_conflict(values: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the winning metric among ``{value, source, ...}`` dicts."""
    if not values:
        return None
    return min(values, key=lambda v: SOURCE_RANK.get(str(v.get("source", "")).upper(), 99))


def build_entities_from_universe(*, include_isin_from_debt: bool = True) -> dict[str, Any]:
    """Build canonical entities from listed-equity meta (+ optional debt ISINs)."""
    universe = load_universe()
    by_cnpj: dict[str, dict[str, Any]] = {}

    for c in universe.get("constituents", []):
        t = normalize_ticker(c.get("ticker", ""))
        if not t:
            continue
        meta = load_meta(t) or {}
        cnpj = normalize_cnpj(meta.get("cnpj") or c.get("cnpj"))
        if not cnpj:
            # still index by ticker-only key
            cnpj = f"TICKER:{t}"
        ent = by_cnpj.get(cnpj) or {
            "cnpj": cnpj if not cnpj.startswith("TICKER:") else "",
            "cvm_code": "",
            "tickers": [],
            "isins": [],
            "company_name": "",
            "category_a": True,
            "sources": ["B3"],
        }
        if t not in ent["tickers"]:
            ent["tickers"].append(t)
        ent["cvm_code"] = str(meta.get("cvm_code") or c.get("cvm_code") or ent["cvm_code"] or "")
        ent["company_name"] = (
            meta.get("company_name") or c.get("company_name") or ent["company_name"] or ""
        )
        if include_isin_from_debt:
            from decifra.config import COMPANIES_DIR

            for name in ("anbima_instruments.csv", "b3_balcao_bonds.csv"):
                path = COMPANIES_DIR / t / "debt" / name
                if not path.exists():
                    continue
                try:
                    import pandas as pd

                    df = pd.read_csv(path, dtype=str)
                    if "isin" in df.columns:
                        for isin in df["isin"].dropna().unique():
                            isin_s = str(isin).strip()
                            if isin_s and isin_s not in ent["isins"]:
                                ent["isins"].append(isin_s)
                    if name.startswith("anbima") and "ANBIMA" not in ent["sources"]:
                        ent["sources"].append("ANBIMA")
                    if name.startswith("b3") and "B3" not in ent["sources"]:
                        ent["sources"].append("B3")
                except Exception:
                    continue
        by_cnpj[cnpj] = ent

    entities = sorted(by_cnpj.values(), key=lambda e: (e.get("cnpj") or "", e["tickers"][0] if e["tickers"] else ""))
    return {"entities": entities, "count": len(entities)}


def resolve_entity(
    *,
    cnpj: str | None = None,
    ticker: str | None = None,
    isin: str | None = None,
    cvm_code: str | None = None,
    entities: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    data = entities or load_entities()
    rows = data.get("entities") or []
    if cnpj:
        c = normalize_cnpj(cnpj)
        for e in rows:
            if normalize_cnpj(e.get("cnpj")) == c:
                return e
    if ticker:
        t = normalize_ticker(ticker)
        for e in rows:
            if t in [normalize_ticker(x) for x in e.get("tickers") or []]:
                return e
    if isin:
        i = isin.strip().upper()
        for e in rows:
            if i in [str(x).upper() for x in e.get("isins") or []]:
                return e
    if cvm_code:
        code = str(cvm_code).strip()
        for e in rows:
            if str(e.get("cvm_code") or "").strip() == code:
                return e
    # Live meta fallback when entities.json empty / miss
    if ticker:
        t = normalize_ticker(ticker)
        meta = load_meta(t)
        if meta:
            return {
                "cnpj": normalize_cnpj(meta.get("cnpj")),
                "cvm_code": str(meta.get("cvm_code") or ""),
                "tickers": [t],
                "isins": [],
                "company_name": meta.get("company_name") or "",
                "category_a": True,
                "sources": ["meta.json"],
            }
    return None


def private_issuer_fallback(cnpj: str) -> dict[str, Any]:
    """Run fallback chain when no Category A equity filings.

    Order: ANBIMA prospectus/debt → B3 Balcão → rating agency stubs.
    """
    from decifra.anbima.debt import load_anbima_source
    from decifra.b3.balcao import load_balcao

    c = normalize_cnpj(cnpj)
    steps: list[dict[str, Any]] = []
    anbima = load_anbima_source()
    anbima_hits = anbima[anbima["cnpj"] == c] if not anbima.empty and "cnpj" in anbima.columns else anbima.iloc[0:0]
    steps.append(
        {
            "step": "ANBIMA",
            "ok": len(anbima_hits) > 0,
            "rows": int(len(anbima_hits)),
            "lineage": {"source_doc": "ANBIMA debt cache"},
        }
    )
    balcao = load_balcao()
    balc_hits = balcao[balcao["cnpj"] == c] if not balcao.empty and "cnpj" in balcao.columns else balcao.iloc[0:0]
    steps.append(
        {
            "step": "B3_BALCAO",
            "ok": len(balc_hits) > 0,
            "rows": int(len(balc_hits)),
            "lineage": {"source_doc": "B3 Balcão cache"},
        }
    )
    # Rating agency parsers not yet implemented — explicit stub step
    steps.append(
        {
            "step": "RATING_AGENCY",
            "ok": False,
            "rows": 0,
            "lineage": {"source_doc": None},
            "note": "Rating press-release parsers not implemented",
        }
    )
    resolved = resolve_entity(cnpj=c)
    category_a = bool(resolved.get("category_a")) if resolved else False
    return {
        "cnpj": c,
        "category_a": category_a,
        "fallback_required": not category_a or resolved is None,
        "hierarchy": list(HIERARCHY_OF_TRUTH),
        "steps": steps,
        "entity": resolved,
    }


def sync_entities(*, write: bool = True) -> dict[str, Any]:
    payload = build_entities_from_universe()
    if write:
        path = save_entities(payload)
        payload["path"] = str(path)
    return payload
