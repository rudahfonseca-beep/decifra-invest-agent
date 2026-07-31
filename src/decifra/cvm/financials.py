from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from decifra.config import CVM_DFP_ZIP, CVM_ITR_ZIP, DEFAULT_FINANCIAL_YEARS
from decifra.cvm.download import ensure_zip, read_csv_from_zip
from decifra.http_util import normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, list_tickers, load_meta, save_meta
from decifra.universe.ibovespa import attach_cnpj_map


STATEMENT_SPECS = {
    "income_statement": {
        "dfp": "DRE_con",
        "itr": "DRE_con",
        "fallback_dfp": "DRE_ind",
        "fallback_itr": "DRE_ind",
    },
    "balance_sheet": {
        "dfp": "BPA_con",
        "itr": "BPA_con",
        "extra_dfp": "BPP_con",
        "extra_itr": "BPP_con",
        "fallback_dfp": "BPA_ind",
        "fallback_itr": "BPA_ind",
        "fallback_extra_dfp": "BPP_ind",
        "fallback_extra_itr": "BPP_ind",
    },
    "cash_flow": {
        "dfp": "DFC_MI_con",
        "itr": "DFC_MI_con",
        "fallback_dfp": "DFC_MI_ind",
        "fallback_itr": "DFC_MI_ind",
    },
}


def _load_statement(zip_path: Path, substr: str) -> pd.DataFrame:
    try:
        return read_csv_from_zip(zip_path, substr)
    except FileNotFoundError:
        return pd.DataFrame()


def _normalize_statement(df: pd.DataFrame, source: str, year: int) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    if "CNPJ_CIA" in df.columns:
        df["CNPJ_NORM"] = df["CNPJ_CIA"].map(normalize_cnpj)
    df["SOURCE_DOC"] = source
    df["SOURCE_YEAR"] = str(year)
    keep = [
        c
        for c in [
            "CNPJ_NORM",
            "CNPJ_CIA",
            "DENOM_CIA",
            "CD_CVM",
            "DT_REFER",
            "DT_FIM_EXERC",
            "VERSAO",
            "CD_CONTA",
            "DS_CONTA",
            "VL_CONTA",
            "ESCALA_MOEDA",
            "MOEDA",
            "ORDEM_EXERC",
            "ST_CONTA_FIXA",
            "SOURCE_DOC",
            "SOURCE_YEAR",
        ]
        if c in df.columns
    ]
    return df[keep]


def _build_cnpj_name_index(frames: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for df in frames:
        if df.empty or "CNPJ_NORM" not in df.columns:
            continue
        cols = [c for c in ["CNPJ_NORM", "DENOM_CIA", "CD_CVM"] if c in df.columns]
        rows.append(df[cols].drop_duplicates())
    if not rows:
        return pd.DataFrame(columns=["CNPJ_NORM", "DENOM_CIA", "CD_CVM"])
    return pd.concat(rows, ignore_index=True).drop_duplicates(subset=["CNPJ_NORM"])


def _match_cnpj_for_ticker(ticker: str, meta: dict[str, Any], name_index: pd.DataFrame) -> str:
    if meta.get("cnpj"):
        return normalize_cnpj(meta["cnpj"])
    stock = (meta.get("stock_name") or meta.get("company_name") or "").upper()
    if not stock or name_index.empty or "DENOM_CIA" not in name_index.columns:
        return ""
    # Try containment both ways
    for _, row in name_index.iterrows():
        denom = str(row.get("DENOM_CIA") or "").upper()
        if not denom:
            continue
        if stock in denom or denom in stock or stock.split()[0] in denom:
            # Prefer stronger matches later; first hit ok for pilot
            return normalize_cnpj(row.get("CNPJ_NORM"))
    stem = "".join(ch for ch in ticker if ch.isalpha())
    hits = name_index[name_index["DENOM_CIA"].fillna("").str.upper().str.contains(stem[:5], regex=False)]
    if len(hits) == 1:
        return normalize_cnpj(hits.iloc[0]["CNPJ_NORM"])
    return ""


def sync_prices(ticker: str) -> Path | None:
    """Fetch OHLCV prices via brapi or yfinance into financials/prices.csv."""
    from decifra.config import BRAPI_API_KEY
    from decifra.http_util import download_json

    root = ensure_company_tree(ticker)
    out = root / "financials" / "prices.csv"
    t = normalize_ticker(ticker)

    df = pd.DataFrame()
    if BRAPI_API_KEY:
        try:
            url = f"https://brapi.dev/api/quote/{t}"
            data = download_json(url, params={"range": "10y", "interval": "1d", "token": BRAPI_API_KEY})
            results = data.get("results") or []
            if results:
                hist = results[0].get("historicalDataPrice") or []
                df = pd.DataFrame(hist)
        except Exception:
            df = pd.DataFrame()

    if df.empty:
        try:
            import yfinance as yf

            hist = yf.Ticker(f"{t}.SA").history(period="10y", auto_adjust=False)
            if not hist.empty:
                hist = hist.reset_index()
                hist.columns = [str(c).lower().replace(" ", "_") for c in hist.columns]
                df = hist
        except Exception:
            df = pd.DataFrame()

    if df.empty:
        return None
    df.to_csv(out, index=False, encoding="utf-8")
    return out


def sync_financials(
    ticker: str | None = None,
    years: list[int] | None = None,
    *,
    include_prices: bool = True,
) -> dict[str, Any]:
    years = years or DEFAULT_FINANCIAL_YEARS
    tickers = list_tickers(ticker)
    if not tickers:
        raise RuntimeError("No universe loaded. Run: decifra sync universe")

    statement_frames: dict[str, list[pd.DataFrame]] = {
        "income_statement": [],
        "balance_sheet": [],
        "cash_flow": [],
    }
    name_frames: list[pd.DataFrame] = []

    for year in years:
        for doc, url_tpl, prefix in (
            ("DFP", CVM_DFP_ZIP, "dfp"),
            ("ITR", CVM_ITR_ZIP, "itr"),
        ):
            zip_path = ensure_zip(url_tpl.format(year=year), f"{prefix}_cia_aberta_{year}.zip")
            for stmt, spec in STATEMENT_SPECS.items():
                key = "dfp" if doc == "DFP" else "itr"
                primary = _normalize_statement(_load_statement(zip_path, spec[key]), doc, year)
                if primary.empty:
                    primary = _normalize_statement(
                        _load_statement(zip_path, spec.get(f"fallback_{key}", "")), doc, year
                    )
                if not primary.empty:
                    statement_frames[stmt].append(primary)
                    name_frames.append(primary[["CNPJ_NORM", "DENOM_CIA", "CD_CVM"]].drop_duplicates())

                extra_key = f"extra_{key}"
                if extra_key in spec:
                    extra = _normalize_statement(_load_statement(zip_path, spec[extra_key]), doc, year)
                    if extra.empty:
                        fb = spec.get(f"fallback_extra_{key}", "")
                        extra = _normalize_statement(_load_statement(zip_path, fb), doc, year)
                    if not extra.empty:
                        statement_frames[stmt].append(extra)
                        name_frames.append(extra[["CNPJ_NORM", "DENOM_CIA", "CD_CVM"]].drop_duplicates())

    name_index = _build_cnpj_name_index(name_frames)
    cnpj_map: dict[str, str] = {}
    written: dict[str, list[str]] = {}

    for t in tickers:
        meta = load_meta(t)
        cnpj = _match_cnpj_for_ticker(t, meta, name_index)
        if cnpj:
            cnpj_map[t] = cnpj
            meta["cnpj"] = cnpj
            if not meta.get("company_name") and not name_index.empty:
                hit = name_index[name_index["CNPJ_NORM"] == cnpj]
                if not hit.empty:
                    meta["company_name"] = str(hit.iloc[0].get("DENOM_CIA") or "")
                    meta["cvm_code"] = str(hit.iloc[0].get("CD_CVM") or meta.get("cvm_code") or "")
            save_meta(t, meta)

        root = ensure_company_tree(t)
        written[t] = []
        if not cnpj:
            continue

        for stmt, frames in statement_frames.items():
            if not frames:
                continue
            all_df = pd.concat(frames, ignore_index=True)
            company_df = all_df[all_df["CNPJ_NORM"] == cnpj].copy()
            if company_df.empty:
                continue
            # Prefer last version per refer date/account
            if "VERSAO" in company_df.columns:
                company_df["VERSAO_NUM"] = pd.to_numeric(company_df["VERSAO"], errors="coerce").fillna(0)
                sort_cols = [c for c in ["DT_REFER", "CD_CONTA", "ORDEM_EXERC", "VERSAO_NUM"] if c in company_df.columns]
                company_df = company_df.sort_values(sort_cols)
                company_df = company_df.drop_duplicates(
                    subset=[c for c in ["DT_REFER", "CD_CONTA", "ORDEM_EXERC", "SOURCE_DOC"] if c in company_df.columns],
                    keep="last",
                )
                company_df = company_df.drop(columns=["VERSAO_NUM"], errors="ignore")
            out = root / "financials" / f"{stmt}.csv"
            company_df.to_csv(out, index=False, encoding="utf-8")
            written[t].append(str(out))

        if include_prices:
            p = sync_prices(t)
            if p:
                written[t].append(str(p))

    if cnpj_map:
        attach_cnpj_map(cnpj_map)

    return {"tickers": len(tickers), "cnpj_mapped": len(cnpj_map), "written": written}
