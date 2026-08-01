import { useEffect, useMemo, useState } from "react";
import { DataTable } from "../DataTable";
import { fetchJson, postJson, qs } from "../../lib/api";
import { fmtMetric, fmtNum } from "../../lib/format";

type Defaults = {
  ticker: string;
  default_peers: string[];
  assumptions: Record<string, number | null>;
  notes: { key: string; label: string; value: number | null; formula: string; rationale: string }[];
  all_tickers: string[];
};

type RunResult = {
  ticker: string;
  dcf: {
    wacc?: number;
    enterprise_value?: number;
    equity_value?: number | null;
    value_per_share?: number | null;
    upside_pct?: number | null;
    current_price?: number | null;
    years?: Record<string, unknown>[];
    warnings?: string[];
  };
  sensitivity?: {
    metric: string;
    wacc_values: number[];
    growth_values: number[];
    grid: (number | null)[][];
  };
  multiples?: {
    subject: Record<string, number | null>;
    peer_multiples: Record<string, number | null>;
    implied_price: Record<string, number | null>;
    implied_price_avg?: number | null;
    warnings?: string[];
  };
  multiple_labels?: Record<string, string>;
  extreme_upside?: boolean;
  assumptions: Record<string, number | null>;
};

const ASSUMP_FIELDS: { key: string; label: string }[] = [
  { key: "revenue_growth_y1", label: "Year-1 revenue growth" },
  { key: "terminal_growth", label: "Terminal growth" },
  { key: "ebit_margin", label: "EBIT margin" },
  { key: "tax_rate", label: "Tax rate" },
  { key: "da_pct_revenue", label: "D&A (% revenue)" },
  { key: "capex_pct_revenue", label: "Capex (% revenue)" },
  { key: "nwc_pct_revenue", label: "ΔNWC (% rev growth)" },
  { key: "beta", label: "Beta" },
  { key: "cost_of_debt", label: "Pre-tax cost of debt" },
  { key: "risk_free_rate", label: "Risk-free rate" },
  { key: "equity_risk_premium", label: "Equity risk premium" },
  { key: "country_risk_premium", label: "Country risk premium" },
];

type Props = {
  initialTicker?: string;
};

export function ValuationView({ initialTicker = "PETR4" }: Props) {
  const [defaults, setDefaults] = useState<Defaults | null>(null);
  const [ticker, setTicker] = useState(initialTicker);
  const [peers, setPeers] = useState<string[]>([]);
  const [stat, setStat] = useState("median");
  const [assumptions, setAssumptions] = useState<Record<string, number>>({});
  const [result, setResult] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTicker(initialTicker);
  }, [initialTicker]);

  useEffect(() => {
    let cancelled = false;
    setBusy(true);
    setError(null);
    fetchJson<Defaults>([
      `/api/valuation/defaults${qs({ ticker })}`,
    ])
      .then((d) => {
        if (cancelled) return;
        setDefaults(d);
        setPeers((prev) =>
          prev.length ? prev : (d.default_peers || []).slice(0, 5)
        );
        const next: Record<string, number> = {};
        for (const f of ASSUMP_FIELDS) {
          const v = d.assumptions[f.key];
          if (typeof v === "number") next[f.key] = v;
        }
        if (typeof d.assumptions.forecast_years === "number") {
          next.forecast_years = d.assumptions.forecast_years;
        }
        setAssumptions(next);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  const peerOptions = useMemo(
    () => (defaults?.all_tickers || []).filter((t) => t !== ticker),
    [defaults, ticker]
  );

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await postJson<RunResult>("/api/valuation/run", {
        ticker,
        peers,
        stat,
        assumptions,
        sensitivity: true,
      });
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function resetDefaults() {
    if (!defaults) return;
    const d = await fetchJson<Defaults>([
      `/api/valuation/defaults${qs({ ticker, peers: peers.join(",") })}`,
    ]);
    setDefaults(d);
    const next: Record<string, number> = {};
    for (const f of ASSUMP_FIELDS) {
      const v = d.assumptions[f.key];
      if (typeof v === "number") next[f.key] = v;
    }
    if (typeof d.assumptions.forecast_years === "number") {
      next.forecast_years = d.assumptions.forecast_years;
    }
    setAssumptions(next);
  }

  const dcf = result?.dcf;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto">
      <h1 className="text-sm font-semibold text-slate-100">Valuation — DCF + multiples</h1>
      <p className="mt-0.5 mb-3 text-[11px] text-slate-500">
        Data-grounded defaults from local CVM + market quotes. Not investment advice.
      </p>

      <div className="mb-3 grid grid-cols-3 gap-3">
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
          Subject ticker
          <select
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
          >
            {(defaults?.all_tickers || [ticker]).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
          Peer statistic
          <select
            value={stat}
            onChange={(e) => setStat(e.target.value)}
            className="rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
          >
            <option value="median">median</option>
            <option value="mean">mean</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
          Forecast years
          <input
            type="number"
            min={2}
            max={10}
            value={assumptions.forecast_years ?? 5}
            onChange={(e) =>
              setAssumptions((a) => ({ ...a, forecast_years: Number(e.target.value) }))
            }
            className="rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
          />
        </label>
      </div>

      <label className="mb-3 flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
        Comparatives
        <select
          multiple
          value={peers}
          onChange={(e) =>
            setPeers(Array.from(e.target.selectedOptions).map((o) => o.value))
          }
          className="h-24 rounded border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-200"
        >
          {peerOptions.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>

      <div className="mb-3 grid grid-cols-3 gap-2">
        {ASSUMP_FIELDS.map((f) => (
          <label
            key={f.key}
            className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500"
          >
            {f.label}
            <input
              type="number"
              step="0.0001"
              value={assumptions[f.key] ?? ""}
              onChange={(e) =>
                setAssumptions((a) => ({ ...a, [f.key]: Number(e.target.value) }))
              }
              className="rounded border border-slate-800 bg-slate-950 px-2 py-1 text-xs tabular-nums text-slate-200"
            />
          </label>
        ))}
      </div>

      <div className="mb-4 flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={run}
          className="rounded-md bg-indigo-500/20 px-3 py-1.5 text-xs text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-50"
        >
          Run valuation
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={resetDefaults}
          className="rounded-md border border-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
        >
          Reset assumptions
        </button>
      </div>

      {error && <p className="mb-2 text-xs text-rose-400">{error}</p>}

      {dcf && (
        <>
          <div className="mb-3 grid grid-cols-4 gap-2">
            {[
              ["WACC", dcf.wacc != null ? `${(dcf.wacc * 100).toFixed(1)}%` : "—"],
              ["Enterprise value", fmtNum(dcf.enterprise_value, 0)],
              ["Equity value", fmtNum(dcf.equity_value, 0)],
              [
                "Value / share",
                dcf.value_per_share != null
                  ? `${fmtNum(dcf.value_per_share, 2)}${
                      dcf.upside_pct != null
                        ? ` (${(dcf.upside_pct * 100).toFixed(1)}%)`
                        : ""
                    }`
                  : "—",
              ],
            ].map(([label, value]) => (
              <div key={label} className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
                <div className="text-sm tabular-nums text-slate-100">{value}</div>
              </div>
            ))}
          </div>
          {result?.extreme_upside && (
            <p className="mb-3 text-xs text-amber-400">
              Defaults are a starting point, not a price target. Implied upside/downside is extreme —
              revisit growth, margins, WACC, and scale before acting.
            </p>
          )}
          {(dcf.warnings || []).map((w) => (
            <p key={w} className="mb-1 text-xs text-amber-400">
              {w}
            </p>
          ))}

          {(dcf.years || []).length > 0 && (
            <>
              <h2 className="mb-2 mt-2 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                FCFF projection
              </h2>
              <DataTable
                rows={dcf.years || []}
                columns={[
                  {
                    key: "year",
                    header: "Year",
                    render: (r) => String(r.year ?? "—"),
                  },
                  {
                    key: "rev",
                    header: "Revenue",
                    render: (r) => fmtNum(r.revenue as number, 0),
                  },
                  {
                    key: "ebit",
                    header: "EBIT",
                    render: (r) => fmtNum(r.ebit as number, 0),
                  },
                  {
                    key: "fcff",
                    header: "FCFF",
                    render: (r) => fmtNum(r.fcff as number, 0),
                  },
                  {
                    key: "pv",
                    header: "PV(FCFF)",
                    render: (r) => fmtNum(r.pv_fcff as number, 0),
                  },
                ]}
              />
            </>
          )}

          {result?.sensitivity && (
            <>
              <h2 className="mb-2 mt-4 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Sensitivity · {result.sensitivity.metric}
              </h2>
              <div className="overflow-auto">
                <table className="w-full border-collapse text-[11px]">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="px-2 py-1 text-left text-slate-400">WACC \\ g</th>
                      {result.sensitivity.growth_values.map((g) => (
                        <th key={g} className="px-2 py-1 text-right text-slate-400">
                          {(g * 100).toFixed(1)}%
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.sensitivity.grid.map((row, i) => (
                      <tr key={i} className="border-b border-slate-800/60 hover:bg-slate-800/20">
                        <td className="px-2 py-1 text-slate-400">
                          {(result.sensitivity!.wacc_values[i] * 100).toFixed(1)}%
                        </td>
                        {row.map((cell, j) => (
                          <td key={j} className="px-2 py-1 text-right tabular-nums text-slate-200">
                            {cell == null ? "—" : fmtNum(cell, 2)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {result?.multiples && (
            <>
              <h2 className="mb-2 mt-4 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Trading multiples
              </h2>
              <DataTable
                rows={Object.keys(result.multiple_labels || {}).map((key) => ({
                  key,
                  label: result.multiple_labels![key],
                  subject: result.multiples!.subject[key],
                  peer: result.multiples!.peer_multiples[key],
                  implied: result.multiples!.implied_price[key],
                }))}
                columns={[
                  { key: "label", header: "Multiple", render: (r) => r.label },
                  {
                    key: "s",
                    header: "Subject",
                    render: (r) => fmtMetric(r.subject, false),
                  },
                  {
                    key: "p",
                    header: "Peer",
                    render: (r) => fmtMetric(r.peer, false),
                  },
                  {
                    key: "i",
                    header: "Implied price",
                    render: (r) => fmtNum(r.implied, 2),
                  },
                ]}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
