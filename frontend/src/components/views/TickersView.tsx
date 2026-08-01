import { DataTable } from "../DataTable";
import { fmtScore } from "../../lib/format";
import type { TickerListItem } from "../../types";

type Props = {
  rows: TickerListItem[];
  loading?: boolean;
  refreshing?: boolean;
  query: string;
  onSelectTicker: (ticker: string) => void;
};

export function TickersView({ rows, loading, refreshing, query, onSelectTicker }: Props) {
  const q = query.trim().toLowerCase();
  const filtered = !q
    ? rows
    : rows.filter(
        (r) =>
          r.ticker.toLowerCase().includes(q) ||
          (r.company || "").toLowerCase().includes(q) ||
          (r.cnpj || "").includes(q.replace(/\D/g, "")) ||
          (r.industry_group || "").toLowerCase().includes(q)
      );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">Ticker list</h1>
          <p className="mt-0.5 text-[11px] text-slate-500">
            Universe with industry, credit score, and financial coverage. Click a row for company
            detail.
            {refreshing ? " · refreshing…" : ""}
          </p>
        </div>
        <div className="text-[10px] text-slate-600">
          {filtered.length} / {rows.length}
        </div>
      </div>
      {loading && rows.length === 0 ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <DataTable
          rows={filtered}
          empty="No tickers match."
          onRowClick={(r) => onSelectTicker(r.ticker)}
          columns={[
            {
              key: "ticker",
              header: "Ticker",
              render: (r) => <span className="font-medium text-slate-100">{r.ticker}</span>,
            },
            {
              key: "company",
              header: "Company",
              render: (r) => r.company || "—",
            },
            {
              key: "industry",
              header: "Industry",
              render: (r) => r.industry_group || "—",
            },
            {
              key: "cohort",
              header: "Cohort",
              render: (r) => r.cohort || "—",
            },
            {
              key: "score",
              header: "Credit",
              render: (r) => <span className="tabular-nums">{fmtScore(r.credit_score)}</span>,
            },
            {
              key: "fin",
              header: "Financials",
              render: (r) =>
                r.has_financials ? (
                  <span className="text-emerald-400">Yes</span>
                ) : (
                  <span className="text-rose-400">No</span>
                ),
            },
            {
              key: "period",
              header: "Period",
              render: (r) => <span className="text-[10px] text-slate-500">{r.period || "—"}</span>,
            },
          ]}
        />
      )}
    </div>
  );
}
