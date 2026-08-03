import { useEffect, useMemo, useState } from "react";
import { DataTable } from "../DataTable";
import { fetchJson, postJson } from "../../lib/api";
import { formatCnpj, groupByCompany } from "../../lib/groupCompanies";

type CovRow = {
  ticker: string;
  cnpj?: string;
  company?: string;
  income_statement?: boolean;
  balance_sheet?: boolean;
  cash_flow?: boolean;
  prices?: boolean;
  notices?: boolean;
  transcripts?: boolean;
  notice_pdfs?: number;
  transcript_files?: number;
  [key: string]: unknown;
};

type CompanyCovRow = {
  key: string;
  company: string;
  cnpj: string;
  tickers: string[];
  primaryTicker: string;
  income_statement: boolean;
  balance_sheet: boolean;
  cash_flow: boolean;
  prices: boolean;
  notices: boolean;
  transcripts: boolean;
  notice_pdfs: number;
  transcript_files: number;
};

type Props = {
  onSelectTicker?: (ticker: string) => void;
  /** Invalidate company list / credit / screener after a successful sync. */
  onResearchDataChanged?: () => void;
};

const YEAR_MIN = 2000;
const YEAR_MAX = 2035;
const DEFAULT_YEAR_FROM = 2020;
const DEFAULT_YEAR_TO = 2026;

function anyBool(members: CovRow[], key: keyof CovRow): boolean {
  return members.some((m) => Boolean(m[key]));
}

function maxNum(members: CovRow[], key: keyof CovRow): number {
  let best = 0;
  for (const m of members) {
    const v = m[key];
    if (typeof v === "number" && v > best) best = v;
  }
  return best;
}

function BoolCell({ ok }: { ok: boolean }) {
  return ok ? <span className="text-emerald-400">Y</span> : <span className="text-rose-400">N</span>;
}

type SyncDialogProps = {
  company: CompanyCovRow;
  onClose: () => void;
  onSynced: (coverage: { rows: CovRow[]; missing_financials: number }) => void;
  onOpenDetail?: (ticker: string) => void;
  onResearchDataChanged?: () => void;
};

function SyncFinancialsDialog({
  company,
  onClose,
  onSynced,
  onOpenDetail,
  onResearchDataChanged,
}: SyncDialogProps) {
  const [selected, setSelected] = useState<string[]>(() => [...company.tickers]);
  const [yearFrom, setYearFrom] = useState(DEFAULT_YEAR_FROM);
  const [yearTo, setYearTo] = useState(DEFAULT_YEAR_TO);
  const [includePrices, setIncludePrices] = useState(true);
  const [addToWatchlist, setAddToWatchlist] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [doneMsg, setDoneMsg] = useState<string | null>(null);

  const missingFin = !company.income_statement || !company.balance_sheet;

  function toggleTicker(t: string) {
    setSelected((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  }

  async function runSync() {
    if (selected.length === 0) {
      setError("Select at least one ticker.");
      return;
    }
    let from = Number(yearFrom);
    let to = Number(yearTo);
    if (!Number.isFinite(from) || !Number.isFinite(to)) {
      setError("Enter a valid year range.");
      return;
    }
    if (from > to) [from, to] = [to, from];
    if (from < YEAR_MIN || to > YEAR_MAX) {
      setError(`Years must be between ${YEAR_MIN} and ${YEAR_MAX}.`);
      return;
    }

    setBusy(true);
    setError(null);
    setDoneMsg(null);
    try {
      const result = await postJson<{
        ok: boolean;
        cnpj_mapped?: number;
        ticker_count?: number;
        years?: number[];
        written?: Record<string, string[]>;
        watchlist?: { added?: string[]; count?: number };
        coverage?: { rows: CovRow[]; missing_financials: number };
        error?: string;
      }>("/api/sync/financials", {
        tickers: selected,
        year_from: from,
        year_to: to,
        include_prices: includePrices,
        add_to_watchlist: addToWatchlist,
      });
      const writtenCount = Object.values(result.written || {}).filter((paths) => paths.length > 0)
        .length;
      const wlAdded = result.watchlist?.added?.length
        ? ` · watchlist +${result.watchlist.added.join(", ")}`
        : addToWatchlist
          ? " · already on watchlist / core"
          : "";
      setDoneMsg(
        `Synced ${selected.join(", ")} for ${from}–${to}. ` +
          `${result.cnpj_mapped ?? 0}/${result.ticker_count ?? selected.length} CNPJ mapped · ` +
          `${writtenCount} ticker(s) wrote files${wlAdded}.`
      );
      if (result.coverage) onSynced(result.coverage);
      onResearchDataChanged?.();
    } catch (e) {
      setError(
        String(e).includes("Failed to fetch") || String(e).includes("8765")
          ? `${e} — start the lake API with \`decifra schemas serve\`.`
          : String(e)
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sync-fin-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-md border border-slate-700 bg-[#0B1120] shadow-xl">
        <div className="border-b border-slate-800 px-4 py-3">
          <h2 id="sync-fin-title" className="text-sm font-semibold text-slate-100">
            Sync financials?
          </h2>
          <p className="mt-1 text-[11px] text-slate-500">
            Download CVM DFP/ITR for this issuer and write lake CSVs. First run for a year may take
            several minutes (large zips).
          </p>
        </div>

        <div className="space-y-3 px-4 py-3">
          <div>
            <div className="text-sm font-medium text-slate-100">{company.company}</div>
            <div className="text-[10px] text-slate-500">CNPJ {formatCnpj(company.cnpj)}</div>
            {missingFin && (
              <div className="mt-1 text-[11px] text-amber-400">
                Income or balance sheet currently missing.
              </div>
            )}
          </div>

          <fieldset>
            <legend className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
              Tickers
            </legend>
            <div className="flex flex-wrap gap-2">
              {company.tickers.map((t) => {
                const on = selected.includes(t);
                return (
                  <label
                    key={t}
                    className={`cursor-pointer rounded border px-2 py-1 text-xs tabular-nums ${
                      on
                        ? "border-indigo-500/60 bg-indigo-500/10 text-slate-100"
                        : "border-slate-700 bg-slate-900 text-slate-500"
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={on}
                      disabled={busy}
                      onChange={() => toggleTicker(t)}
                    />
                    {t}
                  </label>
                );
              })}
            </div>
          </fieldset>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-[11px] text-slate-400">
              Year from
              <input
                type="number"
                min={YEAR_MIN}
                max={YEAR_MAX}
                value={yearFrom}
                disabled={busy}
                onChange={(e) => setYearFrom(Number(e.target.value))}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs tabular-nums text-slate-100 outline-none focus:border-indigo-500"
              />
            </label>
            <label className="block text-[11px] text-slate-400">
              Year to
              <input
                type="number"
                min={YEAR_MIN}
                max={YEAR_MAX}
                value={yearTo}
                disabled={busy}
                onChange={(e) => setYearTo(Number(e.target.value))}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs tabular-nums text-slate-100 outline-none focus:border-indigo-500"
              />
            </label>
          </div>

          <label className="flex items-center gap-2 text-[11px] text-slate-400">
            <input
              type="checkbox"
              checked={includePrices}
              disabled={busy}
              onChange={(e) => setIncludePrices(e.target.checked)}
              className="rounded border-slate-600"
            />
            Also sync prices (brapi / yfinance)
          </label>

          <label className="flex items-center gap-2 text-[11px] text-slate-400">
            <input
              type="checkbox"
              checked={addToWatchlist}
              disabled={busy}
              onChange={(e) => setAddToWatchlist(e.target.checked)}
              className="rounded border-slate-600"
            />
            Add to core watchlist (show in Company list / credit / screener)
          </label>

          {error && <p className="text-xs text-rose-400">{error}</p>}
          {doneMsg && <p className="text-xs text-emerald-400">{doneMsg}</p>}
          {busy && (
            <p className="text-xs italic text-slate-500">
              Syncing… CVM zip download/parse can take a while. Keep this dialog open.
            </p>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-800 px-4 py-3">
          {doneMsg && onOpenDetail && (
            <button
              type="button"
              className="mr-auto text-[11px] text-indigo-400 hover:text-indigo-300"
              onClick={() => onOpenDetail(selected[0] || company.primaryTicker)}
            >
              Open detail →
            </button>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            {doneMsg ? "Close" : "Cancel"}
          </button>
          {!doneMsg && (
            <button
              type="button"
              disabled={busy || selected.length === 0}
              onClick={runSync}
              className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {busy ? "Syncing…" : "Sync financials"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function CoverageView({ onSelectTicker, onResearchDataChanged }: Props) {
  const [rows, setRows] = useState<CovRow[]>([]);
  const [missing, setMissing] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<CompanyCovRow | null>(null);

  function loadCoverage() {
    setLoading(true);
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
  }

  useEffect(() => {
    loadCoverage();
  }, []);

  const companies = useMemo(() => {
    const groups = groupByCompany(
      rows.map((r) => ({
        ...r,
        has_financials: Boolean(r.income_statement && r.balance_sheet),
      }))
    );
    return groups.map(
      (g): CompanyCovRow => ({
        key: g.key,
        company: g.company,
        cnpj: g.cnpj,
        tickers: g.tickers,
        primaryTicker: g.primaryTicker,
        income_statement: anyBool(g.members, "income_statement"),
        balance_sheet: anyBool(g.members, "balance_sheet"),
        cash_flow: anyBool(g.members, "cash_flow"),
        prices: anyBool(g.members, "prices"),
        notices: anyBool(g.members, "notices"),
        transcripts: anyBool(g.members, "transcripts"),
        notice_pdfs: maxNum(g.members, "notice_pdfs"),
        transcript_files: maxNum(g.members, "transcript_files"),
      })
    );
  }, [rows]);

  const missingCompanies = useMemo(
    () => companies.filter((c) => !c.income_statement || !c.balance_sheet).length,
    [companies]
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <h1 className="text-sm font-semibold text-slate-100">Data coverage</h1>
      <p className="mt-0.5 mb-3 text-[11px] text-slate-500">
        One row per issuer (name + CNPJ). Click a company to sync financials (tickers + year range).
        {rows.length > 0
          ? ` · ${companies.length} companies · ${rows.length} tickers`
          : ""}
      </p>
      {(missingCompanies > 0 || missing > 0) && (
        <p className="mb-2 text-xs text-amber-400">
          {missingCompanies > 0
            ? `${missingCompanies} companies missing income or balance sheet`
            : `${missing} tickers missing income or balance sheet`}{" "}
          — click a row to sync from the app, or run `decifra sync financials`.
        </p>
      )}
      {error && <p className="mb-2 text-xs text-rose-400">{error}</p>}
      {loading ? (
        <p className="text-xs italic text-slate-500">Loading…</p>
      ) : (
        <DataTable
          rows={companies}
          empty="No coverage data."
          onRowClick={(r) => setPending(r)}
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
              key: "income_statement",
              header: "Income",
              render: (r) => <BoolCell ok={r.income_statement} />,
            },
            {
              key: "balance_sheet",
              header: "Balance",
              render: (r) => <BoolCell ok={r.balance_sheet} />,
            },
            {
              key: "cash_flow",
              header: "Cash flow",
              render: (r) => <BoolCell ok={r.cash_flow} />,
            },
            {
              key: "prices",
              header: "Prices",
              render: (r) => <BoolCell ok={r.prices} />,
            },
            {
              key: "notices",
              header: "Notices",
              render: (r) => <BoolCell ok={r.notices} />,
            },
            {
              key: "transcripts",
              header: "Transcripts",
              render: (r) => <BoolCell ok={r.transcripts} />,
            },
            {
              key: "notice_pdfs",
              header: "PDFs",
              render: (r) => <span className="tabular-nums">{r.notice_pdfs}</span>,
            },
            {
              key: "transcript_files",
              header: "Files",
              render: (r) => <span className="tabular-nums">{r.transcript_files}</span>,
            },
          ]}
        />
      )}

      {pending && (
        <SyncFinancialsDialog
          company={pending}
          onClose={() => setPending(null)}
          onSynced={(coverage) => {
            setRows(coverage.rows || []);
            setMissing(coverage.missing_financials || 0);
          }}
          onResearchDataChanged={onResearchDataChanged}
          onOpenDetail={
            onSelectTicker
              ? (t) => {
                  setPending(null);
                  onSelectTicker(t);
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
