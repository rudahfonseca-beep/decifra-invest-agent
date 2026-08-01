"""B3 Balcão private corporate bond registrations (fixture-friendly)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from decifra.config import ANBIMA_CACHE_DIR, B3_BALCAO_JSON, ensure_dirs
from decifra.http_util import normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, list_tickers, load_meta


def default_balcao_csv() -> Path:
    return ANBIMA_CACHE_DIR.parent / "b3" / "balcao_bonds.csv"


def write_sample_balcao(path: Path | None = None) -> Path:
    ensure_dirs()
    path = path or default_balcao_csv()
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = pd.DataFrame(
        [
            {
                "cnpj": "33000167000101",
                "isin": "BRPETRDBA001",
                "instrument_type": "DEBENTURE",
                "code": "PETR-BALC-1",
                "issue_date": "2024-03-01",
                "maturity": "2031-03-01",
                "indexer": "CDI+",
                "outstanding_brl": "250000000",
                "source": "B3_BALCAO",
            }
        ]
    )
    sample.to_csv(path, index=False, encoding="utf-8")
    return path


def load_balcao(source_path: Path | None = None) -> pd.DataFrame:
    path = source_path or default_balcao_csv()
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str)
    if "cnpj" in df.columns:
        df["cnpj"] = df["cnpj"].map(normalize_cnpj)
    return df


def sync_b3_bonds(
    *,
    ticker: str | None = None,
    source_path: Path | None = None,
    write_fixture_if_missing: bool = True,
) -> dict[str, Any]:
    ensure_dirs()
    path = source_path or default_balcao_csv()
    if write_fixture_if_missing and not path.exists():
        write_sample_balcao(path)

    df = load_balcao(path)
    tickers = list_tickers(ticker)
    written: list[str] = []
    universe_rows: list[dict[str, Any]] = []

    for t in tickers:
        meta = load_meta(t)
        cnpj = normalize_cnpj(meta.get("cnpj"))
        if not cnpj or df.empty:
            subset = pd.DataFrame()
        else:
            subset = df[df["cnpj"] == cnpj].copy()
        root = ensure_company_tree(t)
        out = root / "debt" / "b3_balcao_bonds.csv"
        subset.to_csv(out, index=False, encoding="utf-8")
        for _, row in subset.iterrows():
            universe_rows.append({**row.to_dict(), "ticker": normalize_ticker(t)})
        if len(subset):
            written.append(t)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(path),
        "bonds": universe_rows,
    }
    B3_BALCAO_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "tickers": len(tickers),
        "bonds": len(universe_rows),
        "written": written,
        "path": str(B3_BALCAO_JSON),
    }
