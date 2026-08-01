"""CVM Formulário de Referência (FRE) zip ingest + company extracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from decifra.config import CVM_CACHE_DIR, CVM_FRE_ZIP, DEFAULT_FRE_YEARS, ensure_dirs
from decifra.cvm.download import ensure_zip, read_all_matching_csvs
from decifra.http_util import normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, list_tickers, load_meta

# Documented field map: FRE CSV columns we surface in company extracts.
FRE_FIELD_MAP = {
    "CNPJ_CIA": "Issuer CNPJ",
    "DENOM_CIA": "Company name",
    "DT_REFER": "Reference date",
    "VERSAO": "FRE version",
    "ID_DOC": "Document id",
    "CD_CVM": "CVM code",
    "CATEGORIA": "FRE category / section",
    "TEXTO": "Section text (when present)",
}


def fre_zip_filename(year: int) -> str:
    return f"fre_cia_aberta_{year}.zip"


def ensure_fre_zip(year: int, *, force: bool = False) -> Path:
    ensure_dirs()
    url = CVM_FRE_ZIP.format(year=year)
    return ensure_zip(url, fre_zip_filename(year), force=force)


def load_fre_frames(zip_path: Path) -> pd.DataFrame:
    """Load FRE CSVs from a zip; empty DataFrame if none match."""
    if not zip_path.exists():
        return pd.DataFrame()
    # Prefer broad match; FRE layouts vary by year/section files
    df = read_all_matching_csvs(zip_path, "fre")
    if df.empty:
        return df
    if "CNPJ_CIA" in df.columns:
        df["CNPJ_NORM"] = df["CNPJ_CIA"].map(normalize_cnpj)
    else:
        df["CNPJ_NORM"] = ""
    df["SOURCE_DOC"] = "FRE"
    df["SOURCE_YEAR"] = zip_path.stem.split("_")[-1] if "_" in zip_path.stem else ""
    return df


def extract_company_fre(df: pd.DataFrame, cnpj: str) -> pd.DataFrame:
    cnpj_n = normalize_cnpj(cnpj)
    if not cnpj_n or df.empty or "CNPJ_NORM" not in df.columns:
        return pd.DataFrame()
    return df[df["CNPJ_NORM"] == cnpj_n].copy()


def write_company_fre(ticker: str, frame: pd.DataFrame, *, year: int) -> Path | None:
    if frame.empty:
        return None
    root = ensure_company_tree(ticker)
    out = root / "fre" / f"fre_{year}.csv"
    frame.to_csv(out, index=False, encoding="utf-8")
    # Compact summary for lineage-friendly consumers
    summary = {
        "ticker": normalize_ticker(ticker),
        "year": year,
        "rows": int(len(frame)),
        "source_doc": "FRE",
        "field_map": FRE_FIELD_MAP,
        "columns": list(frame.columns),
    }
    (root / "fre" / f"fre_{year}_meta.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out


def sync_fre(
    *,
    ticker: str | None = None,
    years: list[int] | None = None,
    force: bool = False,
    from_cache_only: bool = False,
    scope: str = "core",
) -> dict[str, Any]:
    """Download FRE zips (unless from_cache_only) and write per-ticker extracts."""
    years = years or DEFAULT_FRE_YEARS
    tickers = list_tickers(ticker, scope=scope)  # type: ignore[arg-type]
    written: list[str] = []
    errors: list[str] = []

    for year in years:
        zip_path = CVM_CACHE_DIR / fre_zip_filename(year)
        try:
            if from_cache_only:
                if not zip_path.exists():
                    errors.append(f"missing cache {zip_path.name}")
                    continue
            else:
                zip_path = ensure_fre_zip(year, force=force)
            df = load_fre_frames(zip_path)
        except Exception as exc:  # network / zip layout
            errors.append(f"{year}: {exc}")
            continue

        if df.empty:
            errors.append(f"{year}: empty FRE frame")
            continue

        for t in tickers:
            meta = load_meta(t)
            cnpj = meta.get("cnpj") or ""
            subset = extract_company_fre(df, cnpj)
            path = write_company_fre(t, subset, year=year)
            if path:
                written.append(f"{t}:{year}")

    return {
        "tickers": len(tickers),
        "years": years,
        "written": written,
        "errors": errors,
        "field_map": FRE_FIELD_MAP,
    }
