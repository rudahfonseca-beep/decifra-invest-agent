from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from decifra import __version__
from decifra.config import DEFAULT_FINANCIAL_YEARS, DEFAULT_NOTICE_YEARS, ensure_dirs

app = typer.Typer(help="decifra-invest-agent — Ibovespa research data pipeline and CLI", no_args_is_help=True)
sync_app = typer.Typer(help="Sync data from B3/CVM/RI sources")
report_app = typer.Typer(help="Build credit/equity research report prompts and HTML")
app.add_typer(sync_app, name="sync")
app.add_typer(report_app, name="report")
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
        result = build_report_artifacts(report_spec, generate=generate)

    console.print(f"[green]Report artifacts[/green]: {result['dir']}")
    console.print(f"  spec:    {result['spec_path']}")
    console.print(f"  context: {result['context_path']}")
    console.print(f"  prompt:  {result['prompt_path']}")
    if result.get("generated") and result.get("html_path"):
        console.print(f"  html:    {result['html_path']}")
    elif generate and result.get("generate_error"):
        console.print(f"[yellow]{result['generate_error']}[/yellow]")


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
