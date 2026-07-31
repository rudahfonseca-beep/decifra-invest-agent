from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure package import works when launched via `streamlit run path/to/app.py`
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from decifra.assistant.retrieve import coverage_status  # noqa: E402
from decifra.config import OPENAI_API_KEY  # noqa: E402
from decifra.credit.scoring import (  # noqa: E402
    FINANCIAL_RATIOS,
    NON_FINANCIAL_RATIOS,
    build_credit_table,
    peer_medians,
)
from decifra.credit.signals import scan_qualitative_signals  # noqa: E402
from decifra.report.catalog import (  # noqa: E402
    ALL_KPIS,
    KPI_LABELS,
    PCT_KPIS,
    default_kpis,
    kpi_label,
)
from decifra.report.generate import build_report_artifacts  # noqa: E402
from decifra.report.spec import (  # noqa: E402
    EntitySelection,
    ReportSpec,
    SpecValidationError,
    validate_spec,
)


RATIO_LABELS = KPI_LABELS


def _fmt(v: object, pct: bool = False) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    if pct:
        return f"{x * 100:.1f}%"
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:.2f}"


@st.cache_data(show_spinner="Scoring companies from local CVM data…")
def _load_credit_table(include_signals: bool) -> pd.DataFrame:
    return build_credit_table(include_signals=include_signals)


def _render_report_builder(df: pd.DataFrame, include_signals: bool) -> None:
    st.subheader("Report builder")
    st.caption(
        "Pick mode, companies, industries, and KPIs. Export a packed LLM prompt "
        "(always) or generate interactive HTML when OPENAI_API_KEY is set."
    )

    mode = st.radio("Mode", ["credit", "equity"], horizontal=True, key="report_mode")
    title = st.text_input("Title (optional)", value="", key="report_title")
    language = st.selectbox("Language", ["pt", "en"], index=0, key="report_lang")

    all_tickers = sorted(df["ticker"].dropna().unique().tolist())
    all_industries = sorted(df["industry_group"].dropna().unique().tolist())

    c1, c2 = st.columns(2)
    with c1:
        subject_companies = st.multiselect(
            "Subject companies", all_tickers, key="subj_cos"
        )
        subject_industries = st.multiselect(
            "Subject industries", all_industries, key="subj_inds"
        )
    with c2:
        compare_companies = st.multiselect(
            "Comparative companies", all_tickers, key="cmp_cos"
        )
        compare_industries = st.multiselect(
            "Comparative industries", all_industries, key="cmp_inds"
        )

    kpi_options = ALL_KPIS
    defaults = [k for k in default_kpis(mode) if k in kpi_options]  # type: ignore[arg-type]
    if st.session_state.get("_last_report_mode") != mode:
        st.session_state["report_kpis"] = defaults
        st.session_state["_last_report_mode"] = mode
    if "report_kpis" not in st.session_state:
        st.session_state["report_kpis"] = defaults

    selected_kpis = st.multiselect(
        "KPIs",
        options=kpi_options,
        format_func=kpi_label,
        key="report_kpis",
    )

    col_a, col_b = st.columns(2)
    export_clicked = col_a.button("Export prompt", type="primary")
    generate_clicked = col_b.button(
        "Generate HTML",
        disabled=not bool(OPENAI_API_KEY),
        help=None if OPENAI_API_KEY else "Set OPENAI_API_KEY to enable",
    )
    if not OPENAI_API_KEY:
        st.info("OPENAI_API_KEY not set — you can still export the packed prompt.")

    if not (export_clicked or generate_clicked):
        return

    try:
        spec = validate_spec(
            ReportSpec(
                mode=mode,  # type: ignore[arg-type]
                title=title,
                subjects=EntitySelection(
                    companies=subject_companies,
                    industries=subject_industries,
                ),
                comparatives=EntitySelection(
                    companies=compare_companies,
                    industries=compare_industries,
                ),
                kpis=list(selected_kpis),
                include_signals=include_signals,
                language=language,
            ),
            known_tickers=all_tickers,
            known_industries=all_industries,
        )
    except SpecValidationError as exc:
        st.error(str(exc))
        return

    with st.spinner("Building report artifacts…"):
        result = build_report_artifacts(
            spec,
            generate=generate_clicked,
            credit_df=df,
        )

    st.success(f"Wrote artifacts to `{result['dir']}`")
    st.download_button(
        "Download prompt (.md)",
        data=result["prompt_markdown"],
        file_name="report.prompt.md",
        mime="text/markdown",
    )
    st.download_button(
        "Download context (.json)",
        data=json.dumps(result["context"], ensure_ascii=False, indent=2),
        file_name="context.json",
        mime="application/json",
    )
    if result.get("generated") and result.get("html_path"):
        html = Path(result["html_path"]).read_text(encoding="utf-8")
        st.download_button(
            "Download report.html",
            data=html,
            file_name="report.html",
            mime="text/html",
        )
        st.components.v1.html(html, height=720, scrolling=True)
    elif generate_clicked and result.get("generate_error"):
        st.warning(result["generate_error"])

    # Preview: company KPI summary
    rows = []
    for co in result["context"].get("companies") or []:
        if not co.get("found"):
            continue
        row = {
            "role": co.get("role"),
            "ticker": co.get("ticker"),
            "industry": co.get("industry_group"),
        }
        for k, cell in (co.get("kpis") or {}).items():
            row[kpi_label(k)] = cell.get("value")
        rows.append(row)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(
        page_title="Decifra · Creditworthiness",
        page_icon="📊",
        layout="wide",
    )
    st.title("Decifra — Creditworthiness")
    st.caption(
        "Research-grade fundamental credit screen from local CVM financials, "
        "ranked within industry peers. Not a bureau rating."
    )

    with st.sidebar:
        st.header("Filters")
        include_signals = st.checkbox("Include qualitative risk signals", value=True)
        show_incomplete = st.checkbox("Show tickers without financials", value=False)
        refresh = st.button("Refresh scores")
        if refresh:
            _load_credit_table.clear()

    df = _load_credit_table(include_signals)
    if df.empty:
        st.warning("No company data found. Run `decifra sync universe` and `decifra sync financials` first.")
        return

    if not show_incomplete:
        view = df[df["has_financials"]].copy()
    else:
        view = df.copy()

    industries = ["All"] + sorted(view["industry_group"].dropna().unique().tolist())
    industry = st.sidebar.selectbox("Industry group", industries, index=0)

    if industry != "All":
        view = view[view["industry_group"] == industry]

    cohorts = ["All"] + sorted(view["cohort"].dropna().unique().tolist())
    cohort = st.sidebar.selectbox("Scorecard cohort", cohorts, index=0)
    if cohort != "All":
        view = view[view["cohort"] == cohort]

    tab_overview, tab_detail, tab_report, tab_coverage = st.tabs(
        ["Industry overview", "Company detail", "Report builder", "Data coverage"]
    )

    with tab_overview:
        if view.empty:
            st.info("No companies match the current filters.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            scored = view["credit_score"].dropna()
            c1.metric("Companies", len(view))
            c2.metric("Median credit score", _fmt(scored.median()) if len(scored) else "—")
            c3.metric("Mean credit score", _fmt(scored.mean()) if len(scored) else "—")
            c4.metric(
                "With peer benchmark",
                int(view["peer_benchmark"].fillna(False).sum()),
            )

            if industry != "All":
                meds = peer_medians(df, industry)
                if meds:
                    st.subheader(f"Peer median ratios — {industry}")
                    med_cols = st.columns(min(4, len(meds)))
                    for i, (k, v) in enumerate(meds.items()):
                        label = RATIO_LABELS.get(k, k)
                        pct = k in PCT_KPIS
                        med_cols[i % len(med_cols)].metric(label, _fmt(v, pct=pct))

            chart_df = view.dropna(subset=["credit_score"]).sort_values("credit_score")
            if not chart_df.empty:
                try:
                    import plotly.express as px

                    fig = px.bar(
                        chart_df,
                        x="credit_score",
                        y="ticker",
                        color="industry_group",
                        orientation="h",
                        hover_data=["company", "sector", "fundamental_score", "qualitative_penalty"],
                        labels={"credit_score": "Credit score", "ticker": "Ticker"},
                        height=max(360, 28 * len(chart_df)),
                    )
                    fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=40, r=20, t=30, b=40))
                    st.plotly_chart(fig, use_container_width=True)
                except ImportError:
                    st.bar_chart(chart_df.set_index("ticker")["credit_score"])

            display_cols = [
                "ticker",
                "company",
                "industry_group",
                "sector",
                "cohort",
                "period",
                "credit_score",
                "fundamental_score",
                "qualitative_penalty",
                "debt_to_equity",
                "current_ratio",
                "interest_coverage",
                "net_margin",
                "equity_to_assets",
                "roe",
                "peer_benchmark",
                "signal_hits",
            ]
            show = view[[c for c in display_cols if c in view.columns]].copy()
            for col in ("credit_score", "fundamental_score", "qualitative_penalty"):
                if col in show.columns:
                    show[col] = pd.to_numeric(show[col], errors="coerce").round(1)
            st.dataframe(show, use_container_width=True, hide_index=True)

            no_peer = view[~view["peer_benchmark"].fillna(False) & view["has_financials"]]
            if not no_peer.empty:
                st.caption(
                    "No peer benchmark badge: these tickers are alone (or nearly alone) "
                    f"in their industry group — fundamental score defaults to mid-scale (50): "
                    + ", ".join(no_peer["ticker"].tolist())
                )

    with tab_detail:
        tickers = view["ticker"].tolist() if not view.empty else df["ticker"].tolist()
        if not tickers:
            st.info("No tickers available.")
        else:
            ticker = st.selectbox("Company", tickers)
            row = df[df["ticker"] == ticker].iloc[0]
            st.subheader(f"{row['ticker']} — {row['company']}")
            st.write(
                f"**Industry:** {row['industry_group']} · **Sector:** {row['sector'] or '—'} · "
                f"**Cohort:** {row['cohort']} · **Period:** {row['period'] or '—'}"
            )

            m1, m2, m3 = st.columns(3)
            m1.metric("Credit score", _fmt(row.get("credit_score")))
            m2.metric("Fundamental", _fmt(row.get("fundamental_score")))
            m3.metric("Qualitative penalty", _fmt(row.get("qualitative_penalty")))

            if not row.get("peer_benchmark"):
                st.warning("No peer benchmark — industry group has fewer than 2 scored peers.")

            ratio_dirs = (
                FINANCIAL_RATIOS if row["cohort"] == "financial" else NON_FINANCIAL_RATIOS
            )
            meds = peer_medians(df, row["industry_group"])
            ratio_rows = []
            for col, hib in ratio_dirs.items():
                pct = col in PCT_KPIS
                ratio_rows.append(
                    {
                        "Ratio": RATIO_LABELS.get(col, col),
                        "Company": _fmt(row.get(col), pct=pct),
                        "Peer median": _fmt(meds.get(col), pct=pct),
                        "Higher better": "Yes" if hib else "No",
                    }
                )
            st.dataframe(pd.DataFrame(ratio_rows), use_container_width=True, hide_index=True)

            st.subheader("Qualitative risk signals")
            if include_signals:
                scan = scan_qualitative_signals(ticker)
                if not scan["signal_hits"]:
                    st.success("No risk-keyword hits in the last ~24 months of notices/transcripts.")
                else:
                    st.write(
                        f"Penalty **{scan['qualitative_penalty']:.1f}** / 15 · "
                        f"Keywords: {', '.join(scan['matched_keywords']) or '—'}"
                    )
                    hits_df = pd.DataFrame(scan["signal_hits"])
                    if "keywords" in hits_df.columns:
                        hits_df["keywords"] = hits_df["keywords"].apply(
                            lambda x: ", ".join(x) if isinstance(x, list) else x
                        )
                    st.dataframe(
                        hits_df[["source", "date", "title", "keywords", "path", "url"]],
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.info("Enable qualitative signals in the sidebar to scan notices/transcripts.")

    with tab_report:
        _render_report_builder(df, include_signals)

    with tab_coverage:
        cov = pd.DataFrame(coverage_status())
        if cov.empty:
            st.info("No coverage data.")
        else:
            st.dataframe(cov, use_container_width=True, hide_index=True)
            missing = cov[~cov["income_statement"] | ~cov["balance_sheet"]]
            if not missing.empty:
                st.warning(
                    f"{len(missing)} tickers missing income or balance sheet — "
                    "run `decifra sync financials`."
                )


if __name__ == "__main__":
    main()
