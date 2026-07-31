from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from pypdf import PdfReader

from decifra.config import DEFAULT_NOTICE_YEARS, DOWNLOAD_SLEEP_S
from decifra.http_util import download_to_file, normalize_cnpj, normalize_ticker
from decifra.ri.discover import get_ri_url, harvest_ri_document_links
from decifra.store.folders import ensure_company_tree, list_tickers, load_meta


CALL_NEEDLES = (
    "TELECONFER",
    "TRANSCRI",
    "APRESENTA",
    "AUDIO",
    "ÁUDIO",
    "WEBCAST",
    "EARNINGS",
    "RESULTADO",
    "CALL",
)


def _safe_filename(text: str, max_len: int = 80) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in text)
    return cleaned[:max_len].strip("_") or "doc"


def _extract_pdf_text(path: Path, max_chars: int = 200_000) -> str:
    try:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
            if sum(len(p) for p in parts) >= max_chars:
                break
        return "\n".join(parts)[:max_chars].strip()
    except Exception:
        return ""


def _load_ipe_calls(years: list[int]) -> pd.DataFrame:
    from decifra.cvm.notices import _load_ipe_year

    frames = []
    for year in years:
        df = _load_ipe_year(year)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _row_text(row: pd.Series) -> str:
    return " ".join(str(v) for v in row.values if pd.notna(v)).upper()


def sync_transcripts(
    ticker: str | None = None,
    years: list[int] | None = None,
    *,
    download_files: bool = True,
    max_docs_per_ticker: int = 40,
    crawl_ri: bool = True,
) -> dict[str, Any]:
    years = years or DEFAULT_NOTICE_YEARS
    tickers = list_tickers(ticker)
    if not tickers:
        raise RuntimeError("No universe loaded. Run: decifra sync universe")

    ipe = _load_ipe_calls(years)
    written: dict[str, str] = {}

    for t in tickers:
        meta = load_meta(t)
        cnpj = normalize_cnpj(meta.get("cnpj"))
        root = ensure_company_tree(t)
        pdf_dir = root / "transcripts" / "pdfs"
        text_dir = root / "transcripts" / "text"
        index_rows: list[dict[str, Any]] = []

        docs: list[dict[str, Any]] = []
        if cnpj and not ipe.empty and "CNPJ_NORM" in ipe.columns:
            company = ipe[ipe["CNPJ_NORM"] == cnpj]
            for _, row in company.iterrows():
                blob = _row_text(row)
                if not any(n in blob for n in CALL_NEEDLES):
                    continue
                link = ""
                for col in ("LINK_DOC", "Link_Download", "LINK_DOWNLOAD", "URL_DOC", "LINK"):
                    if col in row.index and str(row.get(col) or "").startswith("http"):
                        link = str(row.get(col))
                        break
                title = ""
                for col in ("ASSUNTO", "CATEGORIA", "TIPO", "ESPECIE", "DESCRICAO_TIPO_DOC"):
                    if col in row.index and row.get(col):
                        title = str(row.get(col))
                        break
                date = ""
                for col in ("DT_REFER", "DT_ENTREGA", "DT_DOC"):
                    if col in row.index and row.get(col):
                        date = str(row.get(col))
                        break
                docs.append(
                    {
                        "date": date,
                        "title": title or "call_material",
                        "category": "IPE",
                        "url": link,
                        "source": "IPE",
                    }
                )

        if crawl_ri:
            ri_url = get_ri_url(t)
            for item in harvest_ri_document_links(ri_url):
                docs.append(
                    {
                        "date": "",
                        "title": item["title"],
                        "category": "RI",
                        "url": item["url"],
                        "source": "ri_site",
                    }
                )

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_docs = []
        for d in docs:
            u = d.get("url") or d.get("title")
            if u in seen_urls:
                continue
            seen_urls.add(u)
            unique_docs.append(d)

        count = 0
        for d in unique_docs:
            if count >= max_docs_per_ticker:
                break
            url = d.get("url") or ""
            local_path = ""
            text_path = ""
            if download_files and url.startswith("http"):
                ext = Path(urlparse(url).path).suffix.lower() or ".pdf"
                if ext not in {".pdf", ".html", ".htm", ".mp3", ".mp4"}:
                    ext = ".pdf"
                fname = _safe_filename(f"{d.get('date','')}_{d.get('title','doc')}") + ext
                dest = pdf_dir / fname
                try:
                    if not dest.exists():
                        download_to_file(url, dest)
                        time.sleep(DOWNLOAD_SLEEP_S)
                    local_path = str(dest.relative_to(root))
                    if ext == ".pdf":
                        text = _extract_pdf_text(dest)
                        if text:
                            tp = text_dir / (dest.stem + ".txt")
                            tp.write_text(text, encoding="utf-8")
                            text_path = str(tp.relative_to(root))
                    count += 1
                except Exception:
                    local_path = ""

            index_rows.append(
                {
                    "date": d.get("date", ""),
                    "category": d.get("category", ""),
                    "title": d.get("title", ""),
                    "source": d.get("source", ""),
                    "source_url": url,
                    "local_path": local_path,
                    "text_path": text_path,
                    "ticker": normalize_ticker(t),
                    "cnpj": cnpj,
                }
            )

        out = root / "transcripts" / "index.csv"
        pd.DataFrame(index_rows).to_csv(out, index=False, encoding="utf-8")
        written[t] = str(out)

    return {"tickers": len(tickers), "written": written, "years": years}
