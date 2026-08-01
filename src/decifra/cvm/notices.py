from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from decifra.config import CVM_FATO_CSV, CVM_FATO_ZIP, CVM_IPE_ZIP, DEFAULT_NOTICE_YEARS, DOWNLOAD_SLEEP_S
from decifra.cvm.download import ensure_zip, read_csv_from_zip
from decifra.http_util import download_to_file, normalize_cnpj, normalize_ticker
from decifra.store.folders import ensure_company_tree, list_tickers, load_meta


NOTICE_CATEGORIES = {
    "FATO RELEVANTE",
    "COMUNICADO AO MERCADO",
    "AVISO AOS ACIONISTAS",
    "COMUNICADO À IMPRENSA",
    "COMUNICADO AOS ACIONISTAS",
}


def _is_notice_row(row: pd.Series, cat_col: str | None, title_col: str | None) -> bool:
    text = " ".join(str(row.get(c) or "").upper() for c in (cat_col, title_col, "TIPO", "ESPECIE") if c)
    if not text.strip():
        return True
    for needle in NOTICE_CATEGORIES:
        if needle in text:
            return True
    for needle in ("FATO", "COMUNICADO", "AVISO", "RELEVANTE"):
        if needle in text:
            return True
    return False


def _safe_filename(text: str, max_len: int = 80) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in text)
    return cleaned[:max_len].strip("_") or "doc"


def _normalize_ipe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map Portuguese IPE header variants onto a stable schema."""
    if df.empty:
        return df
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    rename = {
        "CNPJ_Companhia": "CNPJ_CIA",
        "Nome_Companhia": "DENOM_CIA",
        "Codigo_CVM": "CD_CVM",
        "Data_Referencia": "DT_REFER",
        "Data_Entrega": "DT_ENTREGA",
        "Categoria": "CATEGORIA",
        "Tipo": "TIPO",
        "Especie": "ESPECIE",
        "Assunto": "ASSUNTO",
        "Link_Download": "LINK_DOC",
        "LINK_DOWNLOAD": "LINK_DOC",
        "Categoria_Doc": "CATEGORIA",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    cnpj_col = "CNPJ_CIA" if "CNPJ_CIA" in df.columns else None
    if cnpj_col is None:
        for cand in df.columns:
            if "cnpj" in cand.lower():
                cnpj_col = cand
                break
    if cnpj_col:
        df["CNPJ_NORM"] = df[cnpj_col].map(normalize_cnpj)
    return df


def _load_ipe_year(year: int) -> pd.DataFrame:
    zip_path = ensure_zip(CVM_IPE_ZIP.format(year=year), f"ipe_cia_aberta_{year}.zip")
    try:
        df = read_csv_from_zip(zip_path, "ipe_cia_aberta")
    except FileNotFoundError:
        with zipfile.ZipFile(zip_path) as zf:
            csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csvs:
                return pd.DataFrame()
            with zf.open(csvs[0]) as fh:
                df = pd.read_csv(io.BytesIO(fh.read()), sep=";", encoding="latin-1", dtype=str)
    df = _normalize_ipe_columns(df)
    df["SOURCE"] = "IPE"
    df["SOURCE_YEAR"] = str(year)
    return df


def _load_fato_year(year: int) -> pd.DataFrame:
    # Prefer direct CSV; fall back to zip
    csv_url = CVM_FATO_CSV.format(year=year)
    from decifra.config import CVM_CACHE_DIR

    dest = CVM_CACHE_DIR / f"fato_relevante_cia_aberta_{year}.csv"
    try:
        download_to_file(csv_url, dest)
        df = pd.read_csv(dest, sep=";", encoding="latin-1", dtype=str)
    except Exception:
        try:
            zip_path = ensure_zip(CVM_FATO_ZIP.format(year=year), f"fato_relevante_cia_aberta_{year}.zip")
            df = read_csv_from_zip(zip_path, "fato_relevante")
        except Exception:
            return pd.DataFrame()
    df = _normalize_ipe_columns(df)
    df["SOURCE"] = "FATO_RELEVANTE"
    df["SOURCE_YEAR"] = str(year)
    return df


def _link_column(df: pd.DataFrame) -> str | None:
    for col in ("LINK_DOC", "Link_Download", "LINK_DOWNLOAD", "URL_DOC", "LINK"):
        if col in df.columns:
            return col
    return None


def _category_column(df: pd.DataFrame) -> str | None:
    for col in ("CATEGORIA", "Categoria", "CATEGORIA_DOC", "TIPO", "TP_DOC", "ASSUNTO"):
        if col in df.columns:
            return col
    return None


def _title_column(df: pd.DataFrame) -> str | None:
    for col in ("ASSUNTO", "Assunto", "DESCRICAO_TIPO_DOC", "TIPO", "CATEGORIA", "NOME_DOCUMENTO"):
        if col in df.columns:
            return col
    return None


def _date_column(df: pd.DataFrame) -> str | None:
    for col in ("DT_REFER", "Data_Referencia", "DT_ENTREGA", "Data_Entrega", "DT_DOC", "DATA"):
        if col in df.columns:
            return col
    return None


def sync_notices(
    ticker: str | None = None,
    years: list[int] | None = None,
    *,
    download_pdfs: bool = True,
    max_pdfs_per_ticker: int = 80,
    scope: str = "core",
) -> dict[str, Any]:
    years = years or DEFAULT_NOTICE_YEARS
    tickers = list_tickers(ticker, scope=scope)  # type: ignore[arg-type]
    if not tickers:
        raise RuntimeError("No universe loaded. Run: decifra sync universe")

    frames = []
    for year in years:
        frames.append(_load_ipe_year(year))
        frames.append(_load_fato_year(year))
    frames = [f for f in frames if not f.empty]
    if not frames:
        return {"tickers": len(tickers), "written": {}}

    all_docs = pd.concat(frames, ignore_index=True)
    cat_col = _category_column(all_docs)
    title_col = _title_column(all_docs)
    link_col = _link_column(all_docs)
    date_col = _date_column(all_docs)

    written: dict[str, str] = {}
    for t in tickers:
        meta = load_meta(t)
        cnpj = normalize_cnpj(meta.get("cnpj"))
        if not cnpj:
            continue
        if "CNPJ_NORM" not in all_docs.columns:
            continue
        company = all_docs.loc[all_docs["CNPJ_NORM"] == cnpj].copy()
        if company.empty:
            continue
        if cat_col or title_col:
            mask = company.apply(lambda r: _is_notice_row(r, cat_col, title_col), axis=1)
            notices = company.loc[mask].copy()
            if notices.empty:
                notices = company.copy()
        else:
            notices = company.copy()

        root = ensure_company_tree(t)
        pdf_dir = root / "notices" / "pdfs"
        index_rows: list[dict[str, Any]] = []

        # Sort newest first
        if date_col:
            notices = notices.sort_values(date_col, ascending=False)

        pdf_count = 0
        for _, row in notices.iterrows():
            title = str(row.get(title_col) or row.get(cat_col) or "documento")
            category = str(row.get(cat_col) or "")
            date = str(row.get(date_col) or "")
            url = str(row.get(link_col) or "") if link_col else ""
            local_path = ""
            if download_pdfs and url and pdf_count < max_pdfs_per_ticker:
                ext = Path(urlparse(url).path).suffix.lower() or ".pdf"
                if ext not in {".pdf", ".html", ".htm", ".doc", ".docx"}:
                    ext = ".pdf"
                fname = _safe_filename(f"{date}_{category}_{title}") + ext
                dest = pdf_dir / fname
                try:
                    if not dest.exists():
                        download_to_file(url, dest)
                        time.sleep(DOWNLOAD_SLEEP_S)
                    local_path = str(dest.relative_to(root))
                    pdf_count += 1
                except Exception:
                    local_path = ""

            index_rows.append(
                {
                    "date": date,
                    "category": category,
                    "title": title,
                    "source": row.get("SOURCE", ""),
                    "source_year": row.get("SOURCE_YEAR", ""),
                    "source_url": url,
                    "local_path": local_path,
                    "cnpj": cnpj,
                    "ticker": normalize_ticker(t),
                }
            )

        index_df = pd.DataFrame(index_rows)
        out = root / "notices" / "index.csv"
        index_df.to_csv(out, index=False, encoding="utf-8")
        written[t] = str(out)

    return {"tickers": len(tickers), "written": written, "years": years}
