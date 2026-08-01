import { useEffect, useState } from "react";
import { DataTable } from "../DataTable";
import { fetchJson, qs } from "../../lib/api";
import { fmtMetric, fmtScore } from "../../lib/format";
import type { CreditDetail, FilterState, TickerListItem } from "../../types";

type Props = {
  ticker: string;
  tickers: TickerListItem[];
  filters: FilterState;
  onTickerChange: (ticker: string) => void;
};

export function CreditDetailView({ ticker, tickers, filters, onTickerChange }: Props) {
  const [detail, setDetail] = useState<CreditDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchJson<CreditDetail>([
      `/api/credit/${ticker}${qs({ signals: filters.includeSignals })}`,
    ])
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            `${e}. If the API is down, run: .\\.venv\\Scripts\\python.exe -m decifra schemas serve`
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker, filters.includeSignals]);

  const options = tickers.map((t) => t.ticker);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">Company detail</h1>
          <p className="mt-0.5 text-[11px] text-slate-500">
            Credit score vs industry peer medians and qualitative signal scan.
          </p>
        </div>
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
          Company
          <select
            value={ticker}
            onChange={(e) => onTickerChange(e.target.value)}
            className="min-w-[10rem] rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
          >
            {(options.length ? options : [ticker]).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="mb-2 text-xs text-rose-400">{error}</p>}
      {loading && <p className="text-xs italic text-slate-500">Loading…</p>}

      {detail?.found && !loading && (
        <>
          <div className="mb-3 rounded-md border border-slate-800 bg-slate-900 px-3 py-2.5">
            <div className="text-sm text-slate-100">
              {detail.ticker}
              <span className="ml-2 text-xs text-slate-400">{detail.company}</span>
            </div>
            <div className="mt-1 text-[11px] text-slate-500">
              Industry: {detail.industry_group || "—"} · Sector: {detail.sector || "—"} · Cohort:{" "}
              {detail.cohort || "—"} · Period: {detail.period || "—"}
            </div>
          </div>

          <div className="mb-3 grid grid-cols-3 gap-2">
            {[
              ["Credit score", fmtScore(detail.credit_score)],
              ["Fundamental", fmtScore(detail.fundamental_score)],
              ["Qualitative penalty", fmtScore(detail.qualitative_penalty)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
                <div className="text-sm tabular-nums text-slate-100">{value}</div>
              </div>
            ))}
          </div>

          {!detail.peer_benchmark && (
            <p className="mb-3 text-xs text-amber-400">
              No peer benchmark — industry group has fewer than 2 scored peers.
            </p>
          )}

          <h2 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Ratios vs peers
          </h2>
          <DataTable
            rows={detail.ratios || []}
            columns={[
              { key: "label", header: "Ratio", render: (r) => r.label },
              {
                key: "co",
                header: "Company",
                render: (r) => (
                  <span className="tabular-nums">{fmtMetric(r.company, r.pct)}</span>
                ),
              },
              {
                key: "peer",
                header: "Peer median",
                render: (r) => (
                  <span className="tabular-nums">{fmtMetric(r.peer_median, r.pct)}</span>
                ),
              },
              {
                key: "hib",
                header: "Higher better",
                render: (r) => (r.higher_better ? "Yes" : "No"),
              },
            ]}
          />

          <h2 className="mb-2 mt-4 text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Qualitative risk signals
          </h2>
          {!filters.includeSignals && (
            <p className="text-xs text-slate-500">Enable qualitative signals in filters.</p>
          )}
          {filters.includeSignals && detail.signals && (
            <>
              {(detail.signals.signal_hits || []).length === 0 ? (
                <p className="text-xs text-emerald-400">
                  No risk-keyword hits in recent notices/transcripts.
                </p>
              ) : (
                <>
                  <p className="mb-2 text-xs text-slate-400">
                    Penalty {detail.signals.qualitative_penalty?.toFixed(1)} / 15 · Keywords:{" "}
                    {(detail.signals.matched_keywords || []).join(", ") || "—"}
                  </p>
                  <DataTable
                    rows={detail.signals.signal_hits || []}
                    columns={[
                      { key: "source", header: "Source", render: (r) => r.source || "—" },
                      { key: "date", header: "Date", render: (r) => r.date || "—" },
                      { key: "title", header: "Title", render: (r) => r.title || "—" },
                      {
                        key: "kw",
                        header: "Keywords",
                        render: (r) => (r.keywords || []).join(", "),
                      },
                    ]}
                  />
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
