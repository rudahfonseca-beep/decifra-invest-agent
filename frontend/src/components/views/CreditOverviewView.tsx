import { DataTable } from "../DataTable";
import { FilterBar } from "../FilterBar";
import { fmtMetric, fmtScore } from "../../lib/format";
import type { CreditTablePayload, FilterState } from "../../types";

type Props = {
  data: CreditTablePayload | null;
  filters: FilterState;
  loading?: boolean;
  refreshing?: boolean;
  onFilters: (f: FilterState) => void;
  onRefresh: () => void;
  onSelectTicker: (ticker: string) => void;
};

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

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <h1 className="text-sm font-semibold text-slate-100">Industry overview · Credit</h1>
      <p className="mt-0.5 mb-3 text-[11px] text-slate-500">
        Research-grade peer ranks from local CVM financials — not a bureau rating.
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
          ["Companies", summary?.companies ?? "—"],
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
          rows={data?.rows || []}
          empty="No companies match filters."
          onRowClick={(r) => onSelectTicker(r.ticker)}
          columns={[
            {
              key: "ticker",
              header: "Ticker",
              render: (r) => <span className="font-medium text-slate-100">{r.ticker}</span>,
            },
            { key: "company", header: "Company", render: (r) => r.company || "—" },
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
