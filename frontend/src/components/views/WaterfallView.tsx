import { LineageHint } from "../LineageHint";
import { fmtNum } from "../../lib/format";
import type { ValuationWaterfall } from "../../types";

type Props = {
  waterfall: ValuationWaterfall | null;
  loading?: boolean;
  refreshing?: boolean;
};

export function WaterfallView({ waterfall, loading, refreshing }: Props) {
  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <h1 className="text-sm font-semibold text-slate-100">Valuation Waterfall</h1>
      <p className="mt-0.5 mb-4 text-[11px] text-slate-500">
        OCF → FCFE / APV outputs with document provenance
        {refreshing ? " · refreshing…" : ""}
      </p>

      {(loading && !waterfall) || !waterfall ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <>
          <div className="mb-4 rounded-md border border-slate-800 bg-slate-900 px-3 py-2.5">
            <div className="text-sm text-slate-100">
              {waterfall.ticker}
              <span className="ml-2 text-xs text-slate-400">{waterfall.method}</span>
            </div>
            <LineageHint text={waterfall.lineage?.source_doc} />
          </div>

          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Output
                </th>
                <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Value
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(waterfall.outputs || {}).map(([k, v]) => (
                <tr key={k} className="border-b border-slate-800/80 hover:bg-slate-800/30">
                  <td className="px-2 py-2 text-slate-300">{k}</td>
                  <td className="px-2 py-2 tabular-nums text-slate-100">
                    {v == null ? "—" : fmtNum(v, 1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {waterfall.inputs && (
            <div className="mt-6">
              <h2 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Inputs
              </h2>
              <table className="w-full border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      Input
                    </th>
                    <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      Value
                    </th>
                    <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      Lineage
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(waterfall.inputs).map(([k, m]) => (
                    <tr key={k} className="border-b border-slate-800/80 hover:bg-slate-800/30">
                      <td className="px-2 py-2 text-slate-300">{k}</td>
                      <td className="px-2 py-2 tabular-nums text-slate-100">
                        {m.value == null ? "—" : String(m.value)}
                      </td>
                      <td className="px-2 py-2 text-[10px] text-slate-500">
                        {m.lineage?.source_doc || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
