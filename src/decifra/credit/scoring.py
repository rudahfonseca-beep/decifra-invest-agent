from __future__ import annotations

import unicodedata
from typing import Any, Iterable

import pandas as pd

from decifra.credit.metrics import extract_kpis
from decifra.credit.signals import format_signal_summary, scan_qualitative_signals
from decifra.store.folders import list_tickers, load_identity, load_universe

# Free-text CVM/B3 sector → stable industry group
# Expanded mapping to minimise "Other" fallthrough (IMP-007)
SECTOR_TO_GROUP: dict[str, str] = {
    # Energy / Utilities
    "energia eletrica": "Energy",
    "agua e saneamento": "Energy",
    "gas": "Energy",
    # Oil & Gas / Petrochemicals
    "exploracao. refino e distribuicao": "Oil & Gas",
    "distribuicao de combustiveis": "Oil & Gas",
    "petroquimicos": "Oil & Gas",
    "petroleo. gas e biocombustiveis": "Oil & Gas",
    # Banks / Financial
    "bancos": "Banks",
    "seguradoras": "Insurance",
    "previdencia e seguros": "Insurance",
    "servicos financeiros diversos": "Financial Services",
    "securitizadoras de recebiveis": "Financial Services",
    "intermediacao imobiliaria": "Financial Services",
    "bolsas de valores / mercadorias e futuros": "Financial Services",
    # Steel & Mining
    "siderurgia": "Steel & Mining",
    "minerais metalicos": "Steel & Mining",
    "mineracao": "Steel & Mining",
    # Real Estate
    "incorporacoes": "Real Estate",
    "exploracao de imoveis": "Real Estate",
    "construcao civil": "Real Estate",
    "shoppings centers": "Real Estate",
    # Retail & Consumer
    "tecidos. vestuario e calcados": "Retail & Consumer",
    "alimentos": "Retail & Consumer",
    "cervejas e refrigerantes": "Retail & Consumer",
    "carnes e derivados": "Retail & Consumer",
    "eletrodomesticos": "Retail & Consumer",
    "produtos de uso pessoal": "Retail & Consumer",
    "acessorios": "Retail & Consumer",
    "produtos diversos": "Retail & Consumer",
    "comercio e distribuicao": "Retail & Consumer",
    "utilidades domesticas": "Retail & Consumer",
    # Health
    "serv.med.hospit..analises e diagnosticos": "Health",
    "medicamentos e outros produtos": "Health",
    # Telecom / Tech
    "telecomunicacoes": "Telecom",
    "programas e servicos": "Education & Services",
    "computadores e equipamentos": "Telecom",
    # Pulp & Paper
    "papel e celulose": "Pulp & Paper",
    "embalagens": "Pulp & Paper",
    "madeira": "Pulp & Paper",
    # Transport & Infrastructure
    "transporte ferroviario": "Transport & Infra",
    "exploracao de rodovias": "Transport & Infra",
    "aluguel de carros": "Transport & Infra",
    "material rodoviario": "Transport & Infra",
    "transporte aereo": "Transport & Infra",
    "transporte hidroviario": "Transport & Infra",
    "logistica": "Transport & Infra",
    "servicos de apoio e armazenagem": "Transport & Infra",
    # Industrials
    "material aeronautico e de defesa": "Industrials",
    "motores . compressores e outros": "Industrials",
    "maquinas e equipamentos": "Industrials",
    "armas e municoes": "Industrials",
    # Agribusiness
    "agricultura": "Agribusiness",
    "acucar e alcool": "Agribusiness",
    # Education & Services
    "servicos educacionais": "Education & Services",
    "atividades esportivas": "Education & Services",
    "servicos diversos": "Education & Services",
    # Holdings
    "holdings diversificadas": "Holdings",
}

FINANCIAL_GROUPS = {"Banks", "Insurance", "Financial Services"}

# Ratio direction for percentile scoring: True = higher is better
NON_FINANCIAL_RATIOS: dict[str, bool] = {
    "debt_to_equity": False,
    "net_debt_to_cash": False,
    "current_ratio": True,
    "interest_coverage": True,
    "ocf_to_net_debt": True,
    "net_margin": True,
}

FINANCIAL_RATIOS: dict[str, bool] = {
    "equity_to_assets": True,
    "roe": True,
    "net_margin": True,
}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm_sector(sector: str) -> str:
    s = _strip_accents(str(sector or "")).lower().strip()
    s = " ".join(s.split())
    return s


def industry_group(sector: str) -> str:
    key = _norm_sector(sector)
    if key in SECTOR_TO_GROUP:
        return SECTOR_TO_GROUP[key]
    # Fuzzy: try substring / startswith against known keys
    for known, group in SECTOR_TO_GROUP.items():
        if known in key or key in known:
            return group
    return "Other"


def cohort_for_group(group: str) -> str:
    return "financial" if group in FINANCIAL_GROUPS else "non_financial"


def _percentile_rank(series: pd.Series, higher_is_better: bool) -> pd.Series:
    """Rank to 0–100 within peer group; NaNs stay NaN."""
    valid = series.dropna()
    if valid.empty:
        return pd.Series([float("nan")] * len(series), index=series.index)
    if valid.nunique() == 1:
        # No differentiation — give mid score so singles aren't punished
        out = pd.Series([float("nan")] * len(series), index=series.index, dtype=float)
        out.loc[valid.index] = 50.0
        return out
    # percentile rank: fraction of peers strictly below
    ranks = valid.rank(method="average", pct=True) * 100.0
    if not higher_is_better:
        ranks = 100.0 - ranks
    out = pd.Series([float("nan")] * len(series), index=series.index, dtype=float)
    out.loc[ranks.index] = ranks
    return out


def _score_group(df: pd.DataFrame, ratio_dirs: dict[str, bool]) -> pd.Series:
    pct_cols = []
    for col, hib in ratio_dirs.items():
        if col not in df.columns:
            continue
        name = f"_pct_{col}"
        df[name] = _percentile_rank(df[col], hib)
        pct_cols.append(name)
    if not pct_cols:
        return pd.Series([float("nan")] * len(df), index=df.index)
    return df[pct_cols].mean(axis=1, skipna=True)


def build_credit_table(
    tickers: Iterable[str] | None = None,
    *,
    include_signals: bool = True,
) -> pd.DataFrame:
    """Build industry-aware creditworthiness table for local companies."""
    if tickers is None:
        tickers = list_tickers()
    else:
        tickers = [t.upper() for t in tickers]

    # Enrich sector from universe if meta missing
    universe = {
        c["ticker"].upper(): c for c in load_universe().get("constituents", []) if c.get("ticker")
    }

    rows: list[dict[str, Any]] = []
    signal_cache: dict[str, dict[str, Any]] = {}

    for t in tickers:
        kpis = extract_kpis(t)
        meta = load_identity(t)
        sector = kpis.get("sector") or meta.get("sector") or universe.get(t, {}).get("sector") or ""
        if not kpis.get("sector"):
            kpis["sector"] = sector
        group = industry_group(sector)
        cohort = cohort_for_group(group)
        company = kpis.get("company") or universe.get(t, {}).get("company_name") or t

        row: dict[str, Any] = {
            "ticker": t,
            "company": company,
            "sector": sector,
            "cnpj": kpis.get("cnpj") or meta.get("cnpj") or "",
            "isins": kpis.get("isins") or meta.get("isins") or [],
            "industry_group": group,
            "cohort": cohort,
            "period": kpis.get("period") or "",
            "has_financials": bool(kpis.get("has_financials")),
            "peer_benchmark": False,  # filled later
            "revenue": kpis.get("revenue"),
            "ebit": kpis.get("ebit"),
            "net_income": kpis.get("net_income"),
            "gross_debt": kpis.get("gross_debt"),
            "net_debt": kpis.get("net_debt"),
            "equity": kpis.get("equity"),
            "debt_to_equity": kpis.get("debt_to_equity"),
            "net_debt_to_cash": kpis.get("net_debt_to_cash"),
            "current_ratio": kpis.get("current_ratio"),
            "interest_coverage": kpis.get("interest_coverage"),
            "ocf_to_net_debt": kpis.get("ocf_to_net_debt"),
            "net_margin": kpis.get("net_margin"),
            "ebit_margin": kpis.get("ebit_margin"),
            "equity_to_assets": kpis.get("equity_to_assets"),
            "roe": kpis.get("roe"),
            "fundamental_score": None,
            "qualitative_penalty": 0.0,
            "credit_score": None,
            "signal_hits": "",
            "matched_keywords": "",
        }

        if include_signals:
            scan = scan_qualitative_signals(t)
            signal_cache[t] = scan
            row["qualitative_penalty"] = scan["qualitative_penalty"]
            row["signal_hits"] = format_signal_summary(scan)
            row["matched_keywords"] = ", ".join(scan.get("matched_keywords") or [])

        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["fundamental_score"] = float("nan")
    for group, gdf in df.groupby("industry_group", sort=False):
        idx = gdf.index
        cohort = gdf["cohort"].iloc[0]
        ratio_dirs = FINANCIAL_RATIOS if cohort == "financial" else NON_FINANCIAL_RATIOS
        # Only score rows with financials
        scorable = gdf[gdf["has_financials"]].copy()
        peer_count = len(scorable)
        df.loc[idx, "peer_benchmark"] = peer_count >= 2
        if scorable.empty:
            continue
        scores = _score_group(scorable, ratio_dirs)
        df.loc[scores.index, "fundamental_score"] = scores

        # Singleton / no peer: still assign average of available absolute-normalized mid scores
        if peer_count == 1:
            df.loc[scorable.index, "fundamental_score"] = 50.0

    # Credit score = fundamental − qualitative penalty
    fund = pd.to_numeric(df["fundamental_score"], errors="coerce")
    pen = pd.to_numeric(df["qualitative_penalty"], errors="coerce").fillna(0.0)
    df["credit_score"] = (fund - pen).clip(lower=0.0)

    # Sort for display
    df = df.sort_values(
        ["industry_group", "credit_score", "ticker"],
        ascending=[True, False, True],
        na_position="last",
    ).reset_index(drop=True)

    # Attach detailed hits for dashboard (not in main table columns as objects)
    df.attrs["signal_details"] = signal_cache
    return df


def peer_medians(df: pd.DataFrame, industry: str) -> dict[str, float]:
    """Median ratios for an industry group (scored cohort only)."""
    sub = df[(df["industry_group"] == industry) & (df["has_financials"])]
    if sub.empty:
        return {}
    cohort = sub["cohort"].iloc[0]
    cols = list(FINANCIAL_RATIOS if cohort == "financial" else NON_FINANCIAL_RATIOS)
    out: dict[str, float] = {}
    for c in cols:
        if c in sub.columns:
            val = pd.to_numeric(sub[c], errors="coerce").median()
            if pd.notna(val):
                out[c] = float(val)
    return out
