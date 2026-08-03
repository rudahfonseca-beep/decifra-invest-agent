import { useMemo } from "react";
import { DataTable } from "../DataTable";
import { fmtScore } from "../../lib/format";
import { formatCnpj, groupByCompany } from "../../lib/groupCompanies";
import type { TickerListItem } from "../../types";

type Props = {
  rows: TickerListItem[];
  loading?: boolean;
  refreshing?: boolean;
  query: string;
  onSelectTicker: (ticker: string) => void;
};

type CompanyRow = {
  key: string;
  company: string;
  cnpj: string;
  tickers: string[];
  primaryTicker: string;
  industry_group?: string;
  cohort?: string;
  credit_score?: number | null;
  has_financials?: boolean;
  period?: string;
};

export function TickersView({ rows, loading, refreshing, query, onSelectTicker }: Props) {
  const q = query.trim().toLowerCase();
  const digits = q.replace(/\D/g, "");

  const companies = useMemo(() => {
    const groups = groupByCompany(rows);
    const mapped: CompanyRow[] = groups.map((g) => {
      const primary = g.members.find((m) => m.ticker === g.primaryTicker) || g.members[0];
      const anyFin = g.members.some((m) => m.has_financials);
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
        cohort: primary.cohort,
        credit_score: bestScore,
        has_financials: anyFin,
        period: primary.period,
      };
    });

    if (!q) return mapped;
    return mapped.filter(
      (r) =>
        r.company.toLowerCase().includes(q) ||
        r.tickers.some((t) => t.toLowerCase().includes(q)) ||
        (digits.length > 0 && r.cnpj.includes(digits)) ||
        (r.industry_group || "").toLowerCase().includes(q)
    );
  }, [rows, q, digits]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">Company list</h1>
          <p className="mt-0.5 text-[11px] text-slate-500">
            One row per issuer (name + CNPJ). Related tickers listed under the name. Click for
            detail.
            {refreshing ? " · refreshing…" : ""}
          </p>
        </div>
        <div className="text-[10px] text-slate-600">
          {companies.length} companies · {rows.length} tickers
        </div>
      </div>
      {loading && rows.length === 0 ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <DataTable
          rows={companies}
          empty="No companies match."
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
