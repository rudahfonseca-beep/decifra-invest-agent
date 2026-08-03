import { useMemo } from "react";
import { MetricCell } from "./MetricCell";
import { SignalBadge } from "./SignalBadge";
import { fmtNum, fmtPct, fmtRatio } from "../lib/format";
import { formatCnpj, groupByCompany } from "../lib/groupCompanies";
import type { ScreenerRow, Signal } from "../types";

type Props = {
  rows: ScreenerRow[];
  loading?: boolean;
  refreshing?: boolean;
  query?: string;
};

function apvTone(pct: number | null | undefined): Signal | "default" {
  if (pct == null) return "default";
  if (pct >= 10) return "safe";
  if (pct < 0) return "distress";
  return "default";
}

function dscrTone(dscr: number | null | undefined): Signal | "default" {
  if (dscr == null) return "default";
  if (dscr >= 1.5) return "safe";
  if (dscr < 1) return "distress";
  return "warning";
}

function mertonTone(pd: number | null | undefined): Signal | "default" {
  if (pd == null) return "default";
  if (pd >= 10) return "distress";
  if (pd >= 3) return "warning";
  return "safe";
}

function leverageTone(nd: number | null | undefined): Signal | "default" {
  if (nd == null) return "default";
  if (nd >= 5) return "distress";
  if (nd >= 3) return "warning";
  return "default";
}

export function OpportunityScreener({ rows, loading, refreshing, query = "" }: Props) {
  const companies = useMemo(() => {
    const groups = groupByCompany(
      rows.map((r) => ({
        ...r,
        company: r.company_name,
        has_financials: true,
      }))
    );
    const mapped = groups.map((g) => {
      const primary = g.members.find((m) => m.ticker === g.primaryTicker) || g.members[0];
      return { group: g, row: primary as ScreenerRow };
    });
    const q = query.trim().toLowerCase();
    if (!q) return mapped;
    const digits = q.replace(/\D/g, "");
    return mapped.filter(
      ({ group, row }) =>
        group.company.toLowerCase().includes(q) ||
        group.tickers.some((t) => t.toLowerCase().includes(q)) ||
        (digits.length > 0 && group.cnpj.includes(digits)) ||
        (row.isin || "").toLowerCase().includes(q)
    );
  }, [rows, query]);

  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">Cross-Asset Opportunity Screener</h1>
          <p className="mt-0.5 text-[11px] text-slate-500">
            Equity APV and credit leverage / default side-by-side — one row per issuer
          </p>
        </div>
        <div className="text-[10px] text-slate-600">
          {companies.length} companies
          {rows.length !== companies.length ? ` · ${rows.length} tickers` : ""}
          {refreshing ? " · refreshing…" : ""}
        </div>
      </div>

      {loading && rows.length === 0 && (
        <p className="text-xs italic text-slate-500">Loading…</p>
      )}

      {(!loading || rows.length > 0) && (
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-[#0B1120]">
            <tr className="border-b border-slate-800">
              <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Company
              </th>
              <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                APV Disc.
              </th>
              <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                EV / Equity
              </th>
              <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                ND / EBITDA
              </th>
              <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                DSCR
              </th>
              <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Merton PD
              </th>
              <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Signal
              </th>
            </tr>
          </thead>
          <tbody>
            {companies.map(({ group, row }) => (
              <tr
                key={group.key}
                className="border-b border-slate-800/80 text-slate-300 hover:bg-slate-800/30"
              >
                <td className="px-2 py-2.5 align-top">
                  <div className="font-medium text-slate-100">{group.company}</div>
                  <div className="text-[10px] text-slate-500">CNPJ {formatCnpj(group.cnpj)}</div>
                  <div className="mt-0.5 text-[10px] tabular-nums tracking-wide text-slate-400">
                    {group.tickers.join(" · ")}
                  </div>
                </td>
                <td className="px-2 py-2.5 align-top">
                  <MetricCell
                    value={fmtPct(row.apv_discount_pct)}
                    lineage={row.lineage.equity}
                    tone={apvTone(row.apv_discount_pct)}
                  />
                </td>
                <td className="px-2 py-2.5 align-top">
                  <MetricCell value={fmtNum(row.ev_equity, 2)} />
                </td>
                <td className="px-2 py-2.5 align-top">
                  <MetricCell
                    value={fmtRatio(row.net_debt_ebitda)}
                    lineage={row.lineage.credit}
                    tone={leverageTone(row.net_debt_ebitda)}
                  />
                </td>
                <td className="px-2 py-2.5 align-top">
                  <MetricCell value={fmtRatio(row.dscr)} tone={dscrTone(row.dscr)} />
                </td>
                <td className="px-2 py-2.5 align-top">
                  <MetricCell
                    value={fmtPct(row.merton_pd_pct).replace("+", "")}
                    tone={mertonTone(row.merton_pd_pct)}
                  />
                </td>
                <td className="px-2 py-2.5 align-top">
                  <SignalBadge signal={row.signal} />
                </td>
              </tr>
            ))}
            {companies.length === 0 && (
              <tr>
                <td colSpan={7} className="px-2 py-8 text-center text-xs italic text-slate-500">
                  No names match the search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
