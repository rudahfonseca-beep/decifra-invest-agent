import { SignalBadge } from "../SignalBadge";
import { LineageHint } from "../LineageHint";
import { fmtRatio } from "../../lib/format";
import type { CreditDebtMatrix } from "../../types";

type Props = {
  debt: CreditDebtMatrix | null;
  loading?: boolean;
};

export function DebtView({ debt, loading }: Props) {
  const breach = Boolean(debt?.capacity?.any_breach);

  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <h1 className="text-sm font-semibold text-slate-100">Credit & Debt Matrix</h1>
      <p className="mt-0.5 mb-4 text-[11px] text-slate-500">
        Facilities, capacity ratios, and covenant breach status
      </p>

      {loading || !debt ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-start gap-3">
            <div className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Ticker</div>
              <div className="text-sm text-slate-100">{debt.ticker}</div>
              <LineageHint text={debt.as_of ? `As of ${debt.as_of}` : undefined} />
            </div>
            <div className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">ND / EBITDA</div>
              <div className="text-sm tabular-nums text-slate-100">
                {fmtRatio(debt.capacity?.net_debt_ebitda ?? null)}
              </div>
              <LineageHint text={debt.capacity?.lineage?.source_doc} />
            </div>
            <div className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">DSCR</div>
              <div
                className={`text-sm tabular-nums ${
                  (debt.capacity?.dscr ?? 0) >= 1.5
                    ? "text-emerald-400"
                    : (debt.capacity?.dscr ?? 0) < 1
                      ? "text-rose-400"
                      : "text-amber-400"
                }`}
              >
                {fmtRatio(debt.capacity?.dscr ?? null)}
              </div>
            </div>
            <div className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Capacity</div>
              <div className="mt-1">
                <SignalBadge
                  signal={breach ? "distress" : "safe"}
                  label={breach ? "Breach" : "OK"}
                />
              </div>
            </div>
          </div>

          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Code / ISIN
                </th>
                <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Type
                </th>
                <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Indexer
                </th>
                <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Maturity
                </th>
                <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Lineage
                </th>
              </tr>
            </thead>
            <tbody>
              {(debt.facilities || []).map((f, i) => (
                <tr key={i} className="border-b border-slate-800/80 hover:bg-slate-800/30">
                  <td className="px-2 py-2 text-slate-100">{f.isin_or_code}</td>
                  <td className="px-2 py-2 text-slate-300">{f.instrument_type}</td>
                  <td className="px-2 py-2 text-slate-300">{f.indexer}</td>
                  <td className="px-2 py-2 tabular-nums text-slate-300">{f.maturity}</td>
                  <td className="px-2 py-2 text-[10px] text-slate-500">
                    {f.lineage?.source_doc || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
