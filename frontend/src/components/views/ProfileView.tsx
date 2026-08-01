import { LineageHint } from "../LineageHint";
import type { CompanyProfile } from "../../types";

type Props = {
  profile: CompanyProfile | null;
  loading?: boolean;
};

export function ProfileView({ profile, loading }: Props) {
  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <h1 className="text-sm font-semibold text-slate-100">Company Profile</h1>
      <p className="mt-0.5 mb-4 text-[11px] text-slate-500">
        Standardized identity + metrics with source lineage
      </p>

      {loading || !profile ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <>
          <div className="mb-4 rounded-md border border-slate-800 bg-slate-900 px-3 py-2.5">
            <div className="text-sm font-medium text-slate-100">
              {profile.ticker}
              <span className="ml-2 text-xs font-normal text-slate-400">
                {profile.company_name || "—"}
              </span>
            </div>
            <div className="mt-1 text-[11px] text-slate-500">
              CNPJ {profile.cnpj || "—"} · {profile.currency || "BRL"}
            </div>
            <LineageHint text={`ISINs: ${(profile.isins || []).join(", ") || "—"}`} />
          </div>

          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Metric
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
              {Object.entries(profile.metrics || {}).map(([k, m]) => (
                <tr key={k} className="border-b border-slate-800/80 hover:bg-slate-800/30">
                  <td className="px-2 py-2 text-slate-300">{k}</td>
                  <td className="px-2 py-2 tabular-nums text-slate-100">{String(m.value)}</td>
                  <td className="px-2 py-2 text-[10px] text-slate-500">
                    {m.lineage?.source_doc || "—"}
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
