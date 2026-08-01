import { useEffect, useState } from "react";
import { DataTable } from "../DataTable";
import { fetchJson } from "../../lib/api";

type CovRow = Record<string, unknown>;

type Props = {
  onSelectTicker?: (ticker: string) => void;
};

export function CoverageView({ onSelectTicker }: Props) {
  const [rows, setRows] = useState<CovRow[]>([]);
  const [missing, setMissing] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<{ rows: CovRow[]; missing_financials: number }>([
      "/api/coverage",
      "/sample/coverage.json",
    ])
      .then((d) => {
        setRows(d.rows || []);
        setMissing(d.missing_financials || 0);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const keys = rows[0] ? Object.keys(rows[0]) : ["ticker"];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <h1 className="text-sm font-semibold text-slate-100">Data coverage</h1>
      <p className="mt-0.5 mb-3 text-[11px] text-slate-500">
        Per-ticker lake coverage for financials, notices, and transcripts.
      </p>
      {missing > 0 && (
        <p className="mb-2 text-xs text-amber-400">
          {missing} tickers missing income or balance sheet — run `decifra sync financials`.
        </p>
      )}
      {error && <p className="mb-2 text-xs text-rose-400">{error}</p>}
      {loading ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <DataTable
          rows={rows}
          empty="No coverage data."
          onRowClick={
            onSelectTicker
              ? (r) => {
                  const t = String(r.ticker || "");
                  if (t) onSelectTicker(t);
                }
              : undefined
          }
          columns={keys.slice(0, 12).map((k) => ({
            key: k,
            header: k,
            render: (r: CovRow) => {
              const v = r[k];
              if (typeof v === "boolean") {
                return v ? (
                  <span className="text-emerald-400">Y</span>
                ) : (
                  <span className="text-rose-400">N</span>
                );
              }
              return <span className="tabular-nums">{v == null ? "—" : String(v)}</span>;
            },
          }))}
        />
      )}
    </div>
  );
}
