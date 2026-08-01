from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from decifra.config import COMPANIES_DIR
from decifra.http_util import normalize_ticker
from decifra.store.folders import company_dir, list_tickers, load_meta, load_universe


TICKER_RE = re.compile(r"\b([A-Z]{4}\d{1,2}|[A-Z]{3}\d{1,2})\b", re.I)

# Common Portuguese metric aliases → account description needles
METRIC_ALIASES = {
    "receita": ["receita de venda", "receita líquida", "receitas de intermediação", "receita"],
    "receita liquida": ["receita líquida", "receita liquida", "receita de venda"],
    "lucro": ["lucro líquido", "lucro/prejuízo", "lucro liquido"],
    "lucro liquido": ["lucro líquido", "lucro/prejuízo consolidado", "lucro liquido"],
    "ebitda": ["ebitda"],
    "ativo": ["ativo total", "ativo"],
    "passivo": ["passivo total", "passivo"],
    "caixa": ["caixa", "equivalentes de caixa"],
    "divida": ["empréstimos", "financiamentos", "dívida"],
}


def extract_ticker(question: str) -> str | None:
    q = question.upper()
    # Prefer known universe tickers
    universe = {c["ticker"].upper() for c in load_universe().get("constituents", [])}
    # Also match company name tokens
    for c in load_universe().get("constituents", []):
        name = (c.get("stock_name") or "").upper()
        if name and name in q:
            return c["ticker"]
    m = TICKER_RE.search(q)
    if m:
        t = normalize_ticker(m.group(1))
        if not universe or t in universe:
            return t
        return t
    # Partial name match
    for c in load_universe().get("constituents", []):
        name = (c.get("stock_name") or "").upper()
        token = name.split()[0] if name else ""
        if token and len(token) >= 4 and token in q:
            return c["ticker"]
    return None


def extract_year(question: str) -> str | None:
    m = re.search(r"\b(20\d{2})\b", question)
    return m.group(1) if m else None


def coverage_status(
    ticker: str | None = None,
    *,
    scope: str = "all",
) -> list[dict[str, Any]]:
    rows = []
    for t in list_tickers(ticker, scope=scope):  # type: ignore[arg-type]
        root = company_dir(t)
        meta = load_meta(t)
        fin = root / "financials"
        notices = root / "notices" / "index.csv"
        transcripts = root / "transcripts" / "index.csv"
        rows.append(
            {
                "ticker": t,
                "sync_tier": meta.get("sync_tier") or "",
                "cnpj": meta.get("cnpj", ""),
                "company": meta.get("company_name") or meta.get("stock_name") or "",
                "income_statement": (fin / "income_statement.csv").exists(),
                "balance_sheet": (fin / "balance_sheet.csv").exists(),
                "cash_flow": (fin / "cash_flow.csv").exists(),
                "prices": (fin / "prices.csv").exists(),
                "notices": notices.exists() and notices.stat().st_size > 10,
                "transcripts": transcripts.exists() and transcripts.stat().st_size > 10,
                "notice_pdfs": len(list((root / "notices" / "pdfs").glob("*"))) if root.exists() else 0,
                "transcript_files": len(list((root / "transcripts" / "pdfs").glob("*"))) if root.exists() else 0,
            }
        )
    return rows


def search_notices(ticker: str, query: str | None = None, year: str | None = None, limit: int = 20) -> pd.DataFrame:
    path = company_dir(ticker) / "notices" / "index.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str).fillna("")
    if year and "date" in df.columns:
        df = df[df["date"].str.contains(year, na=False)]
    if query:
        q = query.lower()
        mask = df.apply(lambda r: q in " ".join(r.astype(str)).lower(), axis=1)
        df = df[mask]
    return df.head(limit)


def search_transcripts(ticker: str, query: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    root = company_dir(ticker)
    path = root / "transcripts" / "index.csv"
    results: list[dict[str, Any]] = []
    if path.exists():
        df = pd.read_csv(path, dtype=str).fillna("")
        if query:
            q = query.lower()
            df = df[df.apply(lambda r: q in " ".join(r.astype(str)).lower(), axis=1)]
        for _, row in df.head(limit).iterrows():
            item = row.to_dict()
            text_rel = item.get("text_path") or ""
            snippet = ""
            if text_rel:
                tp = root / text_rel
                if tp.exists():
                    text = tp.read_text(encoding="utf-8", errors="ignore")
                    if query:
                        idx = text.lower().find(query.lower())
                        if idx >= 0:
                            snippet = text[max(0, idx - 120) : idx + 280]
                        else:
                            snippet = text[:400]
                    else:
                        snippet = text[:400]
            item["snippet"] = snippet
            results.append(item)
    # Also scan text folder for keyword hits
    if query:
        q = query.lower()
        for tp in (root / "transcripts" / "text").glob("*.txt"):
            text = tp.read_text(encoding="utf-8", errors="ignore")
            if q in text.lower():
                idx = text.lower().find(q)
                results.append(
                    {
                        "title": tp.name,
                        "text_path": str(tp.relative_to(root)),
                        "snippet": text[max(0, idx - 120) : idx + 280],
                        "source": "text_scan",
                    }
                )
            if len(results) >= limit:
                break
    return results[:limit]


def search_financials(ticker: str, question: str, year: str | None = None, limit: int = 15) -> pd.DataFrame:
    root = company_dir(ticker) / "financials"
    q = question.lower()
    needles: list[str] = []
    for key, aliases in METRIC_ALIASES.items():
        if key in q:
            needles.extend(aliases)
    if not needles:
        # use significant tokens
        tokens = [t for t in re.findall(r"[a-zà-ú]{4,}", q) if t not in {"qual", "quais", "para", "sobre", "lista", "mostre", "anos"}]
        needles = tokens[:4]

    frames = []
    for name in ("income_statement.csv", "balance_sheet.csv", "cash_flow.csv"):
        path = root / name
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype=str).fillna("")
        df["STATEMENT"] = name.replace(".csv", "")
        if year and "DT_REFER" in df.columns:
            df = df[df["DT_REFER"].str.contains(year, na=False)]
        if needles and "DS_CONTA" in df.columns:
            mask = False
            for n in needles:
                mask = mask | df["DS_CONTA"].str.lower().str.contains(re.escape(n), na=False)
            df = df[mask]
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    cols = [c for c in ["STATEMENT", "DT_REFER", "CD_CONTA", "DS_CONTA", "VL_CONTA", "ESCALA_MOEDA", "SOURCE_DOC"] if c in out.columns]
    return out[cols].head(limit)
