import { DataTable } from "../DataTable";
import { fmtScore } from "../../lib/format";
import type { IndustryItem } from "../../types";

type Props = {
  items: IndustryItem[];
  loading?: boolean;
  refreshing?: boolean;
  onSelectIndustry: (industry: string) => void;
};

export function IndustriesView({ items, loading, refreshing, onSelectIndustry }: Props) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <h1 className="text-sm font-semibold text-slate-100">Industry list</h1>
      <p className="mt-0.5 mb-3 text-[11px] text-slate-500">
        Industry groups with company counts and median peer credit scores. Click to open credit
        overview filtered to that group.
        {refreshing ? " · refreshing…" : ""}
      </p>
      {loading && items.length === 0 ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <DataTable
          rows={items}
          empty="No industries — run lake API / sync financials."
          onRowClick={(row) => onSelectIndustry(row.industry_group)}
          columns={[
            {
              key: "industry",
              header: "Industry",
              render: (r) => <span className="font-medium text-slate-100">{r.industry_group}</span>,
            },
            {
              key: "cohort",
              header: "Cohort",
              render: (r) => r.cohort || "—",
            },
            {
              key: "n",
              header: "Companies",
              render: (r) => <span className="tabular-nums">{r.companies}</span>,
            },
            {
              key: "med",
              header: "Median score",
              render: (r) => (
                <span className="tabular-nums text-emerald-400">{fmtScore(r.median_credit_score)}</span>
              ),
            },
            {
              key: "mean",
              header: "Mean score",
              render: (r) => <span className="tabular-nums">{fmtScore(r.mean_credit_score)}</span>,
            },
            {
              key: "tickers",
              header: "Tickers",
              render: (r) => (
                <span className="text-[10px] text-slate-500">
                  {r.tickers.slice(0, 6).join(", ")}
                  {r.tickers.length > 6 ? ` +${r.tickers.length - 6}` : ""}
                </span>
              ),
            },
          ]}
        />
      )}
    </div>
  );
}
