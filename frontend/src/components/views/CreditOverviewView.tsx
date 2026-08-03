import { useMemo } from "react";
import { DataTable } from "../DataTable";
import { FilterBar } from "../FilterBar";
import { fmtMetric, fmtScore } from "../../lib/format";
import { formatCnpj, groupByCompany } from "../../lib/groupCompanies";
import type { CreditRow, CreditTablePayload, FilterState } from "../../types";

type Props = {
  data: CreditTablePayload | null;
  filters: FilterState;
  loading?: boolean;
  refreshing?: boolean;
  onFilters: (f: FilterState) => void;
  onRefresh: () => void;
  onSelectTicker: (ticker: string) => void;
};

type CompanyCreditRow = {
  key: string;
  company: string;
  cnpj: string;
  tickers: string[];
  primaryTicker: string;
  industry_group?: string;
  credit_score?: number | null;
  fundamental_score?: number | null;
  qualitative_penalty?: number | null;
  debt_to_equity?: number | null;
  interest_coverage?: number | null;
  net_margin?: number | null;
  peer_benchmark?: boolean;
};

function pickNum(members: CreditRow[], key: keyof CreditRow): number | null {
  for (const m of members) {
    const v = m[key];
    if (typeof v === "number" && !Number.isNaN(v)) return v;
  }
  return null;
}

export function CreditOverviewView({
  data,
  filters,
  loading,
  refreshing,
  onFilters,
  onRefresh,
  onSelectTicker,
}: Props) {
  const summary = data?.summary;
  const meds = data?.peer_medians || {};
  const labels = data?.peer_median_labels || {};
  const pct = new Set(data?.pct_kpis || []);

  const companies = useMemo(() => {
    const groups = groupByCompany(data?.rows || []);
    return groups.map((g): CompanyCreditRow => {
      const primary = (g.members.find((m) => m.ticker === g.primaryTicker) ||
        g.members[0]) as CreditRow;
      const bestScore = g.members.reduce<number | null>((acc, m) => {
        if (m.credit_score == null) return acc;
        if (acc == null) return m.credit_score;
        return Math.max(acc, m.credit_score);
      }, null);
      return {
        key: g.key,
        company: g.company,
        cnpj: g.cnpj,
        tickers: g.tickers,
        primaryTicker: g.primaryTicker,
        industry_group: primary.industry_group,
        credit_score: bestScore,
        fundamental_score: primary.fundamental_score ?? pickNum(g.members as CreditRow[], "fundamental_score"),
        qualitative_penalty:
          primary.qualitative_penalty ?? pickNum(g.members as CreditRow[], "qualitative_penalty"),
        debt_to_equity: primary.debt_to_equity ?? pickNum(g.members as CreditRow[], "debt_to_equity"),
        interest_coverage:
          primary.interest_coverage ?? pickNum(g.members as CreditRow[], "interest_coverage"),
        net_margin: primary.net_margin ?? pickNum(g.members as CreditRow[], "net_margin"),
        peer_benchmark: g.members.some((m) => m.peer_benchmark),
      };
    });
  }, [data?.rows]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <h1 className="text-sm font-semibold text-slate-100">Industry overview · Credit</h1>
      <p className="mt-0.5 mb-3 text-[11px] text-slate-500">
        Research-grade peer ranks from local CVM financials — not a bureau rating. One row per
        issuer; tickers listed under the company name.
        {refreshing ? " · refreshing…" : ""}
      </p>

      <FilterBar
        filters={filters}
        industries={data?.industries || ["All"]}
        cohorts={data?.cohorts || ["All"]}
        onChange={onFilters}
        onRefresh={onRefresh}
      />

      <div className="mb-3 grid grid-cols-4 gap-2">
        {[
          ["Companies", summary?.companies ?? companies.length ?? "—"],
          ["Median score", fmtScore(summary?.median_credit_score ?? null)],
          ["Mean score", fmtScore(summary?.mean_credit_score ?? null)],
          ["Peer benchmark", summary?.with_peer_benchmark ?? "—"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
            <div className="mt-0.5 text-sm tabular-nums text-slate-100">{value}</div>
          </div>
        ))}
      </div>

      {filters.industry !== "All" && Object.keys(meds).length > 0 && (
        <div className="mb-3">
          <div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Peer median ratios — {filters.industry}
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(meds).map(([k, v]) => (
              <div
                key={k}
                className="rounded border border-slate-800 bg-slate-900/80 px-2 py-1.5"
              >
                <div className="text-[10px] text-slate-500">{labels[k] || k}</div>
                <div className="text-xs tabular-nums text-slate-100">
                  {fmtMetric(v, pct.has(k))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && !data ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <DataTable
          rows={companies}
          empty="No companies match filters."
          onRowClick={(r) => onSelectTicker(r.primaryTicker)}
          columns={[
            {
              key: "company",
              header: "Company",
              width: "minmax(220px, 2.5fr)",
              render: (r) => (
                <div>
                  <div className="font-medium text-slate-100">{r.company || "—"}</div>
                  <div className="text-[10px] text-slate-500">CNPJ {formatCnpj(r.cnpj)}</div>
                  <div className="mt-0.5 text-[10px] tabular-nums tracking-wide text-slate-400">
                    {r.tickers.join(" · ")}
                  </div>
                </div>
              ),
            },
            { key: "industry", header: "Industry", render: (r) => r.industry_group || "—" },
            {
              key: "score",
              header: "Credit",
              render: (r) => (
                <span className="tabular-nums text-emerald-400">{fmtScore(r.credit_score)}</span>
              ),
            },
            {
              key: "fund",
              header: "Fundamental",
              render: (r) => <span className="tabular-nums">{fmtScore(r.fundamental_score)}</span>,
            },
            {
              key: "qual",
              header: "Qual. pen.",
              render: (r) => (
                <span className="tabular-nums text-amber-400">
                  {fmtScore(r.qualitative_penalty)}
                </span>
              ),
            },
            {
              key: "dte",
              header: "D/E",
              render: (r) => (
                <span className="tabular-nums">{fmtMetric(r.debt_to_equity, false)}</span>
              ),
            },
            {
              key: "ic",
              header: "Int. cov.",
              render: (r) => (
                <span className="tabular-nums">{fmtMetric(r.interest_coverage, false)}</span>
              ),
            },
            {
              key: "nm",
              header: "Net marg.",
              render: (r) => (
                <span className="tabular-nums">{fmtMetric(r.net_margin, true)}</span>
              ),
            },
            {
              key: "peer",
              header: "Peer",
              render: (r) =>
                r.peer_benchmark ? (
                  <span className="text-emerald-400">Yes</span>
                ) : (
                  <span className="text-slate-500">No</span>
                ),
            },
          ]}
        />
      )}
    </div>
  );
}
