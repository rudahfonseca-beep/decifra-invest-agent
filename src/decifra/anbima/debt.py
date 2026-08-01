"""ANBIMA debentures / CRI / CRA sync — fixture-friendly lake writer.

Live ANBIMA endpoints change often; prefer placing CSV/JSON under
``data/cache/anbima/`` (or pass ``source_path``). Columns expected (flexible):

CNPJ, ISIN, instrument_type, ticker_or_code, yield_pct, indexer, maturity,
covenant_text, outstanding_brl
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from decifra.config import ANBIMA_CACHE_DIR, ensure_dirs
from decifra.http_util import normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, list_tickers, load_meta

CANONICAL_COLS = [
    "cnpj",
    "isin",
    "instrument_type",
    "code",
    "yield_pct",
    "indexer",
    "maturity",
    "covenant_text",
    "outstanding_brl",
    "source",
]


def default_cache_csv() -> Path:
    return ANBIMA_CACHE_DIR / "debt_instruments.csv"


def normalize_anbima_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=CANONICAL_COLS)
    rename = {
        "CNPJ": "cnpj",
        "CNPJ_EMISSOR": "cnpj",
        "ISIN": "isin",
        "TIPO": "instrument_type",
        "instrument": "instrument_type",
        "CODIGO": "code",
        "ticker_or_code": "code",
        "TAXA": "yield_pct",
        "yield": "yield_pct",
        "INDEXADOR": "indexer",
        "VENCIMENTO": "maturity",
        "COVENANT": "covenant_text",
        "covenants": "covenant_text",
        "VOLUME": "outstanding_brl",
        "outstanding": "outstanding_brl",
    }
    out = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for col in CANONICAL_COLS:
        if col not in out.columns:
            out[col] = ""
    out["cnpj"] = out["cnpj"].map(normalize_cnpj)
    out["instrument_type"] = out["instrument_type"].astype(str).str.upper()
    out["indexer"] = out["indexer"].astype(str).str.upper()
    out["source"] = out["source"].replace("", "ANBIMA").fillna("ANBIMA")
    return out[CANONICAL_COLS]


def load_anbima_source(source_path: Path | None = None) -> pd.DataFrame:
    ensure_dirs()
    path = source_path or default_cache_csv()
    if not path.exists():
        return pd.DataFrame(columns=CANONICAL_COLS)
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw if isinstance(raw, list) else raw.get("instruments", [])
        return normalize_anbima_frame(pd.DataFrame(rows))
    return normalize_anbima_frame(pd.read_csv(path, dtype=str))


def write_sample_fixture(path: Path | None = None) -> Path:
    """Write a tiny sample cache so offline sync/tests have data."""
    ensure_dirs()
    path = path or default_cache_csv()
    sample = pd.DataFrame(
        [
            {
                "cnpj": "33000167000101",
                "isin": "BRPETRDBS0A1",
                "instrument_type": "DEBENTURE",
                "code": "PETR11",
                "yield_pct": "1.15",
                "indexer": "CDI+",
                "maturity": "2030-06-15",
                "covenant_text": "Net Debt/EBITDA <= 3.5x",
                "outstanding_brl": "1000000000",
                "source": "ANBIMA",
            },
            {
                "cnpj": "33592510000154",
                "isin": "BRVALECRA001",
                "instrument_type": "CRA",
                "code": "VALE12",
                "yield_pct": "6.50",
                "indexer": "IPCA+",
                "maturity": "2029-12-01",
                "covenant_text": "DSCR >= 1.25x",
                "outstanding_brl": "500000000",
                "source": "ANBIMA",
            },
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(path, index=False, encoding="utf-8")
    return path


def sync_anbima(
    *,
    ticker: str | None = None,
    source_path: Path | None = None,
    write_fixture_if_missing: bool = True,
) -> dict[str, Any]:
    ensure_dirs()
    path = source_path or default_cache_csv()
    if write_fixture_if_missing and not path.exists():
        write_sample_fixture(path)

    df = load_anbima_source(path)
    tickers = list_tickers(ticker)
    written: list[str] = []

    for t in tickers:
        meta = load_meta(t)
        cnpj = normalize_cnpj(meta.get("cnpj"))
        if not cnpj:
            continue
        subset = df[df["cnpj"] == cnpj].copy()
        root = ensure_company_tree(t)
        out = root / "debt" / "anbima_instruments.csv"
        subset.to_csv(out, index=False, encoding="utf-8")
        meta_out = {
            "ticker": normalize_ticker(t),
            "cnpj": cnpj,
            "rows": int(len(subset)),
            "source": "ANBIMA",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "lineage": {"source_doc": str(path.name)},
        }
        (root / "debt" / "anbima_meta.json").write_text(
            json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if len(subset):
            written.append(t)

    # Universe-level cache copy
    universe_cache = ANBIMA_CACHE_DIR / "debt_instruments_normalized.csv"
    df.to_csv(universe_cache, index=False, encoding="utf-8")

    return {
        "tickers": len(tickers),
        "instruments": int(len(df)),
        "written": written,
        "source": str(path),
    }
