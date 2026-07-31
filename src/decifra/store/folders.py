from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decifra.config import COMPANIES_DIR, IBOVESPA_JSON, ensure_dirs
from decifra.http_util import normalize_ticker


def company_dir(ticker: str) -> Path:
    return COMPANIES_DIR / normalize_ticker(ticker)


def ensure_company_tree(ticker: str) -> Path:
    ensure_dirs()
    root = company_dir(ticker)
    for sub in (
        root / "financials",
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


def save_meta(ticker: str, meta: dict[str, Any]) -> Path:
    ensure_company_tree(ticker)
    meta = {**meta, "ticker": normalize_ticker(ticker)}
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = meta_path(ticker)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_universe() -> dict[str, Any]:
    if not IBOVESPA_JSON.exists():
        return {"constituents": []}
    return json.loads(IBOVESPA_JSON.read_text(encoding="utf-8"))


def list_tickers(ticker: str | None = None) -> list[str]:
    if ticker:
        return [normalize_ticker(ticker)]
    data = load_universe()
    return [normalize_ticker(c["ticker"]) for c in data.get("constituents", [])]
