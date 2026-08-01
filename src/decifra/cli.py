from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from decifra import __version__
from decifra.config import (
    DEFAULT_FINANCIAL_YEARS,
    DEFAULT_FORECAST_YEARS,
    DEFAULT_FRE_YEARS,
    DEFAULT_NOTICE_YEARS,
    ensure_dirs,
)

app = typer.Typer(help="decifra-invest-agent — Ibovespa research data pipeline and CLI", no_args_is_help=True)
sync_app = typer.Typer(help="Sync data from B3/CVM/RI sources")
entities_app = typer.Typer(help="Entity graph: CNPJ/CVM/ticker/ISIN + private-issuer fallback")
report_app = typer.Typer(help="Build credit/equity research report prompts and HTML")
valuation_app = typer.Typer(help="Equity valuation: DCF (FCFF/WACC) and trading multiples")
app.add_typer(sync_app, name="sync")
app.add_typer(entities_app, name="entities")
app.add_typer(report_app, name="report")
app.add_typer(valuation_app, name="valuation")
console = Console()


def _parse_years(years: Optional[str], default: list[int]) -> list[int]:
    if not years:
        return default
    years = years.strip()
    if "-" in years and "," not in years:
        a, b = years.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x.strip()) for x in years.split(",") if x.strip()]


@app.callback()
def main() -> None:
    ensure_dirs()


@app.command()
def version() -> None:
    """Show package version."""
    console.print(__version__)


@sync_app.command("universe")
def sync_universe_cmd(
    force_cadastro: bool = typer.Option(False, help="Re-download CVM cadastro"),
    b3_cnpj: bool = typer.Option(True, help="Enrich CNPJ via B3 listed companies API"),
    force_cnpj: bool = typer.Option(False, help="Re-resolve CNPJ even if already set"),
) -> None:
    """Fetch Ibovespa constituents and create company folders."""
    from decifra.universe.ibovespa import sync_universe
    from decifra.universe.b3_cnpj import enrich_constituents_with_b3
    from decifra.config import IBOVESPA_JSON
    from decifra.store.folders import save_meta, ensure_company_tree

    with console.status("Syncing Ibovespa universe..."):
        payload = sync_universe(force_cadastro=force_cadastro)
        if b3_cnpj:
            console.print("Enriching CNPJ via B3...")
            enriched = enrich_constituents_with_b3(payload["constituents"], force=force_cnpj)
            payload["constituents"] = enriched
            IBOVESPA_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            for c in enriched:
                ensure_company_tree(c["ticker"])
                save_meta(
                    c["ticker"],
                    {
                        "ticker": c["ticker"],
                        "stock_name": c.get("stock_name"),
                        "type": c.get("type"),
                        "cnpj": c.get("cnpj", ""),
                        "cvm_code": c.get("cvm_code", ""),
                        "company_name": c.get("company_name", ""),
                        "ri_url": c.get("ri_url", ""),
                        "sector": c.get("sector", ""),
                        "part_pct": c.get("part_pct"),
                        "issuing_company": c.get("issuing_company", ""),
                        "source": "ibovespa",
                    },
                )
    mapped = sum(1 for c in payload["constituents"] if c.get("cnpj"))
    console.print(f"[green]Universe OK[/green]: {payload['count']} tickers, {mapped} with CNPJ")
    console.print(f"Saved: {IBOVESPA_JSON}")


@sync_app.command("financials")
def sync_financials_cmd(
    ticker: Optional[str] = typer.Option(None, help="Single ticker, e.g. PETR4"),
    years: Optional[str] = typer.Option(None, help="Year range, e.g. 2020-2026"),
    no_prices: bool = typer.Option(False, help="Skip OHLCV prices"),
) -> None:
    """Download CVM DFP/ITR and write per-company financial CSVs."""
    from decifra.cvm.financials import sync_financials

    y = _parse_years(years, DEFAULT_FINANCIAL_YEARS)
    with console.status("Syncing financials (this downloads large CVM ZIPs)..."):
        result = sync_financials(ticker=ticker, years=y, include_prices=not no_prices)
    console.print(
        f"[green]Financials OK[/green]: {result['cnpj_mapped']}/{result['tickers']} tickers mapped"
    )


@sync_app.command("notices")
def sync_notices_cmd(
    ticker: Optional[str] = typer.Option(None, help="Single ticker"),
    years: Optional[str] = typer.Option(None, help="Year range, e.g. 2023-2026"),
    no_pdfs: bool = typer.Option(False, help="Metadata only"),
    max_pdfs: int = typer.Option(80, help="Max PDFs per ticker"),
) -> None:
    """Sync fatos relevantes / comunicados from CVM IPE."""
    from decifra.cvm.notices import sync_notices

    y = _parse_years(years, DEFAULT_NOTICE_YEARS)
    with console.status("Syncing notices..."):
        result = sync_notices(
            ticker=ticker, years=y, download_pdfs=not no_pdfs, max_pdfs_per_ticker=max_pdfs
        )
    console.print(f"[green]Notices OK[/green]: wrote indexes for {len(result['written'])} tickers")


@sync_app.command("transcripts")
def sync_transcripts_cmd(
    ticker: Optional[str] = typer.Option(None, help="Single ticker"),
    years: Optional[str] = typer.Option(None, help="Year range"),
    no_download: bool = typer.Option(False, help="Index only"),
    no_ri: bool = typer.Option(False, help="Skip RI site crawl"),
    max_docs: int = typer.Option(40, help="Max docs per ticker"),
) -> None:
    """Collect earnings call / presentation materials."""
    from decifra.ri.calls import sync_transcripts

    y = _parse_years(years, DEFAULT_NOTICE_YEARS)
    with console.status("Syncing transcripts / call materials..."):
        result = sync_transcripts(
            ticker=ticker,
            years=y,
            download_files=not no_download,
            max_docs_per_ticker=max_docs,
            crawl_ri=not no_ri,
        )
    console.print(f"[green]Transcripts OK[/green]: wrote indexes for {len(result['written'])} tickers")


@sync_app.command("fre")
def sync_fre_cmd(
    ticker: Optional[str] = typer.Option(None, help="Single ticker"),
    years: Optional[str] = typer.Option(None, help="Year range, e.g. 2022-2026"),
    force: bool = typer.Option(False, help="Re-download FRE zips"),
    cache_only: bool = typer.Option(False, help="Only use data/cache/cvm FRE zips"),
) -> None:
    """Download CVM Formulário de Referência (FRE) and write company extracts."""
    from decifra.cvm.fre import sync_fre

    y = _parse_years(years, DEFAULT_FRE_YEARS)
    with console.status("Syncing FRE..."):
        result = sync_fre(ticker=ticker, years=y, force=force, from_cache_only=cache_only)
    console.print(
        f"[green]FRE OK[/green]: {len(result['written'])} extracts · "
        f"{len(result.get('errors') or [])} warnings"
    )


@sync_app.command("anbima")
def sync_anbima_cmd(
    ticker: Optional[str] = typer.Option(None, help="Single ticker"),
) -> None:
    """Sync ANBIMA debentures/CRI/CRA into company debt folders (cache/fixture)."""
    from decifra.anbima import sync_anbima

    with console.status("Syncing ANBIMA debt instruments..."):
        result = sync_anbima(ticker=ticker)
    console.print(
        f"[green]ANBIMA OK[/green]: {result['instruments']} instruments · "
        f"wrote {len(result['written'])} tickers"
    )


@sync_app.command("b3-shares")
def sync_b3_shares_cmd(
    ticker: Optional[str] = typer.Option(None, help="Single ticker"),
    force: bool = typer.Option(False, help="Refresh all rows"),
) -> None:
    """Build B3 shares/mcap universe artifact from local meta (+ optional network)."""
    from decifra.b3 import sync_b3_shares

    with console.status("Syncing B3 shares artifact..."):
        result = sync_b3_shares(ticker=ticker, force=force)
    console.print(f"[green]B3 shares OK[/green]: {len(result['updated'])} tickers -> {result['path']}")


@sync_app.command("b3-bonds")
def sync_b3_bonds_cmd(
    ticker: Optional[str] = typer.Option(None, help="Single ticker"),
) -> None:
    """Sync B3 Balcão bond registrations into company debt folders."""
    from decifra.b3 import sync_b3_bonds

    with console.status("Syncing B3 Balcão bonds..."):
        result = sync_b3_bonds(ticker=ticker)
    console.print(
        f"[green]B3 Balcão OK[/green]: {result['bonds']} bonds · wrote {len(result['written'])} tickers"
    )


@sync_app.command("all")
def sync_all_cmd(
    ticker: Optional[str] = typer.Option(None, help="Limit to one ticker after universe sync"),
    years: Optional[str] = typer.Option(None, help="Years for notices/transcripts"),
    financial_years: Optional[str] = typer.Option(None, help="Years for DFP/ITR"),
) -> None:
    """Run full pipeline: universe → financials → notices → transcripts."""
    sync_universe_cmd()
    sync_financials_cmd(ticker=ticker, years=financial_years, no_prices=False)
    sync_notices_cmd(ticker=ticker, years=years, no_pdfs=False, max_pdfs=40)
    sync_transcripts_cmd(ticker=ticker, years=years, no_download=False, no_ri=False, max_docs=20)


@entities_app.command("sync")
def entities_sync_cmd() -> None:
    """Build data/universe/entities.json from Ibovespa meta + debt ISINs."""
    from decifra.entities.resolve import sync_entities

    with console.status("Building entity graph..."):
        result = sync_entities(write=True)
    console.print(
        f"[green]Entities OK[/green]: {result.get('count', 0)} entities -> {result.get('path', '')}"
    )


@entities_app.command("resolve")
def entities_resolve_cmd(
    ticker: Optional[str] = typer.Option(None, help="B3 ticker"),
    cnpj: Optional[str] = typer.Option(None, help="CNPJ digits or formatted"),
    isin: Optional[str] = typer.Option(None, help="ISIN"),
    cvm_code: Optional[str] = typer.Option(None, "--cvm", help="CVM code"),
) -> None:
    """Resolve CNPJ <-> CVM <-> ticker <-> ISIN via entities.json (+ meta fallback)."""
    from decifra.entities.resolve import resolve_entity

    if not any([ticker, cnpj, isin, cvm_code]):
        console.print("[red]Provide --ticker, --cnpj, --isin, or --cvm[/red]")
        raise typer.Exit(2)
    ent = resolve_entity(ticker=ticker, cnpj=cnpj, isin=isin, cvm_code=cvm_code)
    if not ent:
        console.print("[yellow]No entity found[/yellow]")
        raise typer.Exit(1)
    console.print_json(json.dumps(ent, ensure_ascii=False))


@entities_app.command("private-issuer")
def entities_private_issuer_cmd(
    cnpj: str = typer.Option(..., help="Issuer CNPJ"),
) -> None:
    """Run private-issuer fallback chain (ANBIMA -> Balcao -> rating stub)."""
    from decifra.entities.resolve import private_issuer_fallback

    result = private_issuer_fallback(cnpj)
    console.print_json(json.dumps(result, ensure_ascii=False))


@app.command("status")
def status_cmd(ticker: Optional[str] = typer.Option(None, help="Single ticker")) -> None:
    """Show local data coverage for Ibovespa companies."""
    from decifra.assistant.retrieve import coverage_status

    rows = coverage_status(ticker)
    table = Table(title="decifra coverage")
    for col in (
        "ticker",
        "cnpj",
        "company",
        "income_statement",
        "balance_sheet",
        "cash_flow",
        "prices",
        "notices",
        "transcripts",
        "notice_pdfs",
        "transcript_files",
    ):
        table.add_column(col)
    for r in rows:
        table.add_row(
            r["ticker"],
            r["cnpj"] or "-",
            (r["company"] or "-")[:28],
            "Y" if r["income_statement"] else ".",
            "Y" if r["balance_sheet"] else ".",
            "Y" if r["cash_flow"] else ".",
            "Y" if r["prices"] else ".",
            "Y" if r["notices"] else ".",
            "Y" if r["transcripts"] else ".",
            str(r["notice_pdfs"]),
            str(r["transcript_files"]),
        )
    console.print(table)


@app.command("ask")
def ask_cmd(
    question: str = typer.Argument(..., help="Research question in PT or EN"),
    json_out: bool = typer.Option(False, "--json", help="Print raw JSON"),
) -> None:
    """Answer a research question from local company data."""
    from decifra.assistant.ask import answer_question

    result = answer_question(question)
    if json_out:
        console.print_json(json.dumps(result, ensure_ascii=False))
        return
    if not result.get("ok"):
        console.print(f"[red]{result.get('error')}[/red]")
        raise typer.Exit(1)
    console.print(f"[bold]{result['ticker']}[/bold] · intent={result['intent']} · year={result.get('year')}")
    console.print(result.get("answer") or "")


@app.command("merton")
def merton_cmd(
    asset_value: float = typer.Option(..., help="Asset value V"),
    debt_face: float = typer.Option(..., help="Debt face value D"),
    risk_free: float = typer.Option(0.07, help="Risk-free rate"),
    horizon: float = typer.Option(1.0, help="Horizon years T"),
    asset_vol: float = typer.Option(..., help="Asset volatility sigma_V"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON"),
) -> None:
    """Merton structural model / Distance to Default."""
    from decifra.credit.merton import merton_dtd

    result = merton_dtd(
        asset_value=asset_value,
        debt_face=debt_face,
        risk_free=risk_free,
        horizon_years=horizon,
        asset_vol=asset_vol,
    )
    if json_out:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return
    console.print(
        f"Equity={result.equity_value:,.2f}  DtD={result.distance_to_default:.3f}  "
        f"PD={result.default_probability:.2%}"
    )


@app.command("capacity")
def capacity_cmd(
    net_debt: float = typer.Option(..., help="Net debt"),
    ebitda: float = typer.Option(..., help="EBITDA"),
    ocf: float = typer.Option(..., help="OCF or EBITDA proxy for DSCR numerator"),
    debt_service: float = typer.Option(..., help="Debt service (interest + mandatory amort)"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON"),
) -> None:
    """Debt capacity flags: ND/EBITDA <= 3.5x and DSCR >= 1.25x."""
    from decifra.credit.capacity import evaluate_capacity

    result = evaluate_capacity(
        net_debt=net_debt,
        ebitda=ebitda,
        ocf_or_ebitda_proxy=ocf,
        debt_service=debt_service,
    )
    if json_out:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return
    nd = result.net_debt_ebitda
    ds = result.dscr
    console.print(
        f"ND/EBITDA={nd.value} (breach={nd.breach})  DSCR={ds.value} (breach={ds.breach})  "
        f"any_breach={result.any_breach}"
    )


@app.command("credit")
def credit_cmd(
    industry: Optional[str] = typer.Option(None, help="Filter by industry group, e.g. Energy"),
    no_signals: bool = typer.Option(False, help="Skip notices/transcripts keyword scan"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON rows"),
) -> None:
    """Show industry-peer creditworthiness scores from local CVM data."""
    from decifra.credit.scoring import build_credit_table

    with console.status("Scoring companies..."):
        df = build_credit_table(include_signals=not no_signals)
    if df.empty:
        console.print("[yellow]No company data. Run sync universe + financials first.[/yellow]")
        raise typer.Exit(1)
    if industry:
        key = industry.strip().lower()
        df = df[df["industry_group"].str.lower() == key]
        if df.empty:
            console.print(f"[yellow]No rows for industry group '{industry}'.[/yellow]")
            raise typer.Exit(1)
    if json_out:
        console.print_json(df.to_json(orient="records", force_ascii=False))
        return
    table = Table(title="Creditworthiness (industry peer scores)")
    for col in (
        "ticker",
        "industry_group",
        "cohort",
        "credit_score",
        "fundamental_score",
        "qualitative_penalty",
        "peer_benchmark",
        "period",
    ):
        table.add_column(col)
    for _, r in df.iterrows():
        def _s(v: object) -> str:
            if v is None or (isinstance(v, float) and (v != v)):
                return "-"
            if isinstance(v, float):
                return f"{v:.1f}"
            return str(v)

        table.add_row(
            str(r["ticker"]),
            str(r["industry_group"]),
            str(r["cohort"]),
            _s(r["credit_score"]),
            _s(r["fundamental_score"]),
            _s(r["qualitative_penalty"]),
            "Y" if r.get("peer_benchmark") else ".",
            str(r.get("period") or "-")[:10],
        )
    console.print(table)


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


@report_app.command("build")
def report_build_cmd(
    mode: str = typer.Option("credit", help="Report mode: credit or equity"),
    company: Optional[str] = typer.Option(
        None, help="Subject company tickers (comma-separated)"
    ),
    industry: Optional[str] = typer.Option(
        None, help="Subject industry groups (comma-separated)"
    ),
    compare_company: Optional[str] = typer.Option(
        None, help="Comparative company tickers (comma-separated)"
    ),
    compare_industry: Optional[str] = typer.Option(
        None, help="Comparative industry groups (comma-separated)"
    ),
    kpi: Optional[str] = typer.Option(
        None, help="KPI keys (comma-separated); default = mode pack"
    ),
    title: Optional[str] = typer.Option(None, help="Report title"),
    language: str = typer.Option("pt", help="pt or en"),
    no_signals: bool = typer.Option(False, help="Skip qualitative risk signals"),
    spec: Optional[str] = typer.Option(None, "--spec", help="Path to report spec JSON"),
    generate: bool = typer.Option(
        False, "--generate", help="Call LLM to produce report.html (needs OPENAI_API_KEY)"
    ),
    offline: bool = typer.Option(
        False, "--offline", help="Render HTML from context.json (Jinja2+Plotly, no LLM)"
    ),
) -> None:
    """Assemble report context and write prompt (and optional HTML) under data/reports/."""
    from decifra.report.generate import build_report_artifacts
    from decifra.report.spec import (
        EntitySelection,
        ReportSpec,
        SpecValidationError,
        load_spec,
        validate_spec,
    )

    try:
        if spec:
            report_spec = load_spec(spec)
        else:
            report_spec = validate_spec(
                ReportSpec(
                    mode=mode.lower().strip(),  # type: ignore[arg-type]
                    title=title or "",
                    subjects=EntitySelection(
                        companies=_split_csv(company),
                        industries=_split_csv(industry),
                    ),
                    comparatives=EntitySelection(
                        companies=_split_csv(compare_company),
                        industries=_split_csv(compare_industry),
                    ),
                    kpis=_split_csv(kpi),
                    include_signals=not no_signals,
                    language=language.lower().strip(),
                )
            )
    except (SpecValidationError, ValueError, OSError, json.JSONDecodeError) as exc:
        console.print(f"[red]Invalid report spec:[/red] {exc}")
        raise typer.Exit(1)

    with console.status("Building report artifacts..."):
        result = build_report_artifacts(report_spec, generate=generate, offline=offline)

    console.print(f"[green]Report artifacts[/green]: {result['dir']}")
    console.print(f"  spec:    {result['spec_path']}")
    console.print(f"  context: {result['context_path']}")
    console.print(f"  prompt:  {result['prompt_path']}")
    if result.get("generated") and result.get("html_path"):
        console.print(f"  html:    {result['html_path']}")
    elif generate and result.get("generate_error"):
        console.print(f"[yellow]{result['generate_error']}[/yellow]")


def _assumption_overrides_from_flags(
    *,
    growth: Optional[float],
    terminal_growth: Optional[float],
    ebit_margin: Optional[float],
    tax_rate: Optional[float],
    wacc: Optional[float],
    risk_free: Optional[float],
    erp: Optional[float],
    country_risk: Optional[float],
    beta: Optional[float],
    cost_of_debt: Optional[float],
) -> dict:
    pairs = (
        ("revenue_growth_y1", growth),
        ("terminal_growth", terminal_growth),
        ("ebit_margin", ebit_margin),
        ("tax_rate", tax_rate),
        ("wacc_override", wacc),
        ("risk_free_rate", risk_free),
        ("equity_risk_premium", erp),
        ("country_risk_premium", country_risk),
        ("beta", beta),
        ("cost_of_debt", cost_of_debt),
    )
    return {k: v for k, v in pairs if v is not None}


@valuation_app.command("dcf")
def valuation_dcf_cmd(
    ticker: str = typer.Option(..., "--ticker", help="Subject ticker, e.g. PETR4"),
    peers: Optional[str] = typer.Option(
        None, "--peers", help="Comparable tickers for beta fallback (comma-separated)"
    ),
    years: int = typer.Option(DEFAULT_FORECAST_YEARS, "--years", help="Explicit forecast horizon"),
    growth: Optional[float] = typer.Option(None, "--growth", help="Override year-1 revenue growth"),
    terminal_growth: Optional[float] = typer.Option(None, "--terminal-growth"),
    ebit_margin: Optional[float] = typer.Option(None, "--ebit-margin"),
    tax_rate: Optional[float] = typer.Option(None, "--tax-rate"),
    wacc: Optional[float] = typer.Option(None, "--wacc", help="Override WACC directly (bypasses CAPM)"),
    risk_free: Optional[float] = typer.Option(None, "--risk-free"),
    erp: Optional[float] = typer.Option(None, "--erp"),
    country_risk: Optional[float] = typer.Option(None, "--country-risk"),
    beta: Optional[float] = typer.Option(None, "--beta"),
    cost_of_debt: Optional[float] = typer.Option(None, "--cost-of-debt"),
    assumptions_path: Optional[str] = typer.Option(
        None, "--assumptions", help="JSON file with full assumption overrides"
    ),
    json_out: bool = typer.Option(False, "--json", help="Print raw JSON"),
) -> None:
    """Run the FCFF/WACC DCF for one ticker; prints computed defaults unless overridden."""
    from pathlib import Path

    from decifra.valuation.assumptions import DcfAssumptions, build_default_assumptions
    from decifra.valuation.dcf import discount_cash_flow

    peer_list = _split_csv(peers)
    overrides = _assumption_overrides_from_flags(
        growth=growth,
        terminal_growth=terminal_growth,
        ebit_margin=ebit_margin,
        tax_rate=tax_rate,
        wacc=wacc,
        risk_free=risk_free,
        erp=erp,
        country_risk=country_risk,
        beta=beta,
        cost_of_debt=cost_of_debt,
    )
    if assumptions_path:
        overrides = {**json.loads(Path(assumptions_path).read_text(encoding="utf-8")), **overrides}

    with console.status(f"Running DCF for {ticker.upper()}..."):
        defaults, _ = build_default_assumptions(ticker, peers=peer_list, forecast_years=years)
        merged = {**defaults.to_dict(), **overrides}
        assumptions = DcfAssumptions.from_dict(merged)
        result = discount_cash_flow(ticker, assumptions, peers=peer_list)

    if json_out:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return

    console.print(f"[bold]{result.ticker}[/bold] DCF — WACC {result.wacc:.1%} ({result.wacc_source})")
    table = Table(title="FCFF projection")
    for col in ("Year", "Growth", "Revenue", "EBIT", "FCFF", "PV(FCFF)"):
        table.add_column(col)
    for y in result.years:
        table.add_row(
            str(y.year),
            f"{y.growth:.1%}",
            f"{y.revenue:,.0f}",
            f"{y.ebit:,.0f}",
            f"{y.fcff:,.0f}",
            f"{y.pv_fcff:,.0f}",
        )
    console.print(table)
    console.print(f"Enterprise value: {result.enterprise_value:,.0f}")
    console.print(f"Net debt: {result.net_debt:,.0f}" if result.net_debt is not None else "Net debt: -")
    console.print(
        f"Equity value: {result.equity_value:,.0f}" if result.equity_value is not None else "Equity value: -"
    )
    if result.value_per_share is not None:
        upside = f"{result.upside_pct:.1%}" if result.upside_pct is not None else "-"
        price = f"{result.current_price:.2f}" if result.current_price is not None else "-"
        console.print(f"Value per share: {result.value_per_share:.2f} (current: {price}, upside {upside})")
    for w in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {w}")


@valuation_app.command("apv")
def valuation_apv_cmd(
    fcff: str = typer.Option(..., help="Comma-separated unlevered FCFF path"),
    ku: float = typer.Option(..., "--ku", help="Unlevered cost of capital"),
    interest: Optional[str] = typer.Option(None, help="Comma-separated interest path"),
    tax_rate: float = typer.Option(0.34, help="Corporate tax rate"),
    distress_pv: float = typer.Option(0.0, help="PV of financial distress costs"),
    terminal_growth: float = typer.Option(0.0, help="Gordon growth on terminal FCFF"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON"),
) -> None:
    """Adjusted Present Value: V_L = V_U + PV(tax shield) - PV(distress)."""
    from decifra.valuation.apv import compute_apv

    fcff_path = [float(x) for x in _split_csv(fcff)]
    interest_path = [float(x) for x in _split_csv(interest)] if interest else None
    result = compute_apv(
        unlevered_fcff=fcff_path,
        unlevered_cost_of_capital=ku,
        debt_interest=interest_path,
        tax_rate=tax_rate,
        distress_cost_pv=distress_pv,
        terminal_growth=terminal_growth,
    )
    if json_out:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return
    console.print(f"V_U={result.v_u:,.2f}  PV(TS)={result.pv_tax_shield:,.2f}  "
                  f"PV(distress)={result.pv_distress_costs:,.2f}  V_L={result.v_l:,.2f}")


@valuation_app.command("waterfall")
def valuation_waterfall_cmd(
    ocf: float = typer.Option(..., help="Operating cash flow"),
    interest: float = typer.Option(..., help="Interest expense"),
    amortization: float = typer.Option(0.0, help="Mandatory debt amortization"),
    equity_capex: float = typer.Option(0.0, help="Equity-financed capex"),
    net_borrowing: float = typer.Option(0.0, help="Net borrowing (+ inflow)"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON"),
) -> None:
    """OCF -> mandatory debt service -> residual FCFE waterfall."""
    from decifra.valuation.waterfall import ocf_to_fcfe_waterfall

    result = ocf_to_fcfe_waterfall(
        ocf=ocf,
        interest=interest,
        mandatory_amortization=amortization,
        capex_equity_financed=equity_capex,
        net_borrowing=net_borrowing,
    )
    if json_out:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return
    console.print(
        f"OCF={result.ocf:,.2f}  debt_service={result.debt_service:,.2f}  "
        f"FCFE={result.fcfe:,.2f}  covered={result.covered}"
    )


@valuation_app.command("multiples")
def valuation_multiples_cmd(
    ticker: str = typer.Option(..., "--ticker", help="Subject ticker, e.g. PETR4"),
    peers: str = typer.Option(..., "--peers", help="Comparable tickers (comma-separated)"),
    stat: str = typer.Option("median", "--stat", help="Peer aggregation: median or mean"),
    json_out: bool = typer.Option(False, "--json", help="Print raw JSON"),
) -> None:
    """Trading multiples (P/E, EV/EBITDA, EV/Revenue, EV/EBIT, P/B) vs. user-chosen comparables."""
    from decifra.valuation.multiples import MULTIPLE_LABELS, relative_valuation

    peer_list = _split_csv(peers)
    with console.status(f"Computing multiples for {ticker.upper()}..."):
        result = relative_valuation(ticker, peer_list, stat=stat)

    if json_out:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return

    console.print(
        f"[bold]{result.ticker}[/bold] relative valuation vs {result.peer_count} peer(s) ({stat})"
    )
    table = Table(title="Multiples")
    for col in ("Multiple", "Subject", "Peer", "Implied price"):
        table.add_column(col)

    def _s(v: Optional[float]) -> str:
        return f"{v:.2f}" if v is not None else "-"

    for key, label in MULTIPLE_LABELS.items():
        table.add_row(
            label,
            _s(getattr(result.subject, key)),
            _s(result.peer_multiples.get(key)),
            _s(result.implied_price.get(key)),
        )
    console.print(table)
    if result.implied_price_avg is not None:
        console.print(
            f"Implied range: {_s(result.implied_price_low)} - {_s(result.implied_price_high)} "
            f"(avg {_s(result.implied_price_avg)}) vs current price {_s(result.subject.price)}"
        )
    for w in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {w}")


@valuation_app.command("build")
def valuation_build_cmd(
    ticker: Optional[str] = typer.Option(None, "--ticker", help="Subject ticker (ignored if --spec given)"),
    peers: Optional[str] = typer.Option(None, "--peers", help="Comparable tickers (comma-separated)"),
    stat: str = typer.Option("median", "--stat", help="Peer aggregation: median or mean"),
    years: int = typer.Option(DEFAULT_FORECAST_YEARS, "--years", help="Explicit forecast horizon"),
    assumptions_path: Optional[str] = typer.Option(
        None, "--assumptions", help="JSON file with DCF assumption overrides"
    ),
    title: Optional[str] = typer.Option(None, "--title", help="Valuation title"),
    spec: Optional[str] = typer.Option(None, "--spec", help="Path to valuation spec JSON"),
) -> None:
    """Assemble the full DCF + multiples context and write artifacts under data/valuations/."""
    from pathlib import Path

    from decifra.valuation.generate import build_valuation_artifacts
    from decifra.valuation.spec import (
        SpecValidationError,
        ValuationSpec,
        load_spec,
        validate_spec,
    )

    try:
        if spec:
            val_spec = load_spec(spec)
        else:
            if not ticker:
                console.print("[red]--ticker is required unless --spec is given[/red]")
                raise typer.Exit(1)
            overrides: dict = {}
            if assumptions_path:
                overrides.update(json.loads(Path(assumptions_path).read_text(encoding="utf-8")))
            val_spec = validate_spec(
                ValuationSpec(
                    ticker=ticker,
                    comparatives=_split_csv(peers),
                    dcf_assumptions=overrides,
                    multiples_stat=stat,
                    forecast_years=years,
                    title=title or "",
                )
            )
    except (SpecValidationError, ValueError, OSError, json.JSONDecodeError) as exc:
        console.print(f"[red]Invalid valuation spec:[/red] {exc}")
        raise typer.Exit(1)

    with console.status("Building valuation artifacts..."):
        result = build_valuation_artifacts(val_spec)

    console.print(f"[green]Valuation artifacts[/green]: {result['dir']}")
    console.print(f"  spec:     {result['spec_path']}")
    console.print(f"  context:  {result['context_path']}")
    console.print(f"  markdown: {result['markdown_path']}")


@app.command("dashboard")
def dashboard_cmd(
    port: int = typer.Option(8501, help="Streamlit port"),
) -> None:
    """Launch the Streamlit creditworthiness dashboard."""
    import subprocess
    from pathlib import Path

    try:
        import streamlit  # noqa: F401
    except ImportError:
        console.print(
            "[red]Streamlit not installed.[/red] Run: pip install -e \".[dashboard]\""
        )
        raise typer.Exit(1)

    app_path = Path(__file__).resolve().parent / "dashboard" / "app.py"
    console.print(f"Starting dashboard: {app_path}")
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app_path),
                "--server.port",
                str(port),
            ]
        )
    )


if __name__ == "__main__":
    app()
