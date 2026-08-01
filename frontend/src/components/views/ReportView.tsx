import { useEffect, useState } from "react";
import { fetchJson, postJson } from "../../lib/api";

type Catalog = {
  modes: string[];
  languages: string[];
  kpis: { key: string; label: string }[];
  default_kpis: { credit: string[]; equity: string[] };
  tickers: string[];
  industries: string[];
};

type BuildResult = {
  ok: boolean;
  error?: string;
  prompt_markdown?: string;
  context?: unknown;
  dir?: string;
  generated?: boolean;
  generate_error?: string;
};

function MultiSelect({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string[];
  onChange: (v: string[]) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
      {label}
      <select
        multiple
        value={value}
        onChange={(e) =>
          onChange(Array.from(e.target.selectedOptions).map((o) => o.value))
        }
        className="h-28 rounded border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-200"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ReportView() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [mode, setMode] = useState<"credit" | "equity">("credit");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("pt");
  const [subjCos, setSubjCos] = useState<string[]>([]);
  const [subjInds, setSubjInds] = useState<string[]>([]);
  const [cmpCos, setCmpCos] = useState<string[]>([]);
  const [cmpInds, setCmpInds] = useState<string[]>([]);
  const [kpis, setKpis] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BuildResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    fetchJson<Catalog>(["/api/report/catalog"])
      .then((c) => {
        setCatalog(c);
        setKpis(c.default_kpis.credit || []);
      })
      .catch((e) =>
        setError(
          `${e}. Start the lake API: .\\.venv\\Scripts\\python.exe -m decifra schemas serve`
        )
      );
  }, []);

  useEffect(() => {
    if (!catalog) return;
    setKpis(catalog.default_kpis[mode] || []);
  }, [mode, catalog]);

  async function build(generate: boolean) {
    setBusy(true);
    setError(null);
    try {
      const res = await postJson<BuildResult>("/api/report/build", {
        mode,
        title,
        language,
        subject_companies: subjCos,
        subject_industries: subjInds,
        compare_companies: cmpCos,
        compare_industries: cmpInds,
        kpis,
        include_signals: true,
        generate,
      });
      setResult(res);
      if (!res.ok) setError(res.error || "Build failed");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto">
      <h1 className="text-sm font-semibold text-slate-100">Report builder</h1>
      <p className="mt-0.5 mb-3 text-[11px] text-slate-500">
        Pack an LLM prompt from local KPIs; optional HTML when OPENAI_API_KEY is set on the API
        host.
      </p>

      {!catalog && !error && <p className="text-xs italic text-slate-500">Loading catalog…</p>}
      {error && <p className="mb-2 text-xs text-rose-400">{error}</p>}

      {catalog && (
        <>
          <div className="mb-3 grid grid-cols-3 gap-3">
            <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
              Mode
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as "credit" | "equity")}
                className="rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
              >
                {catalog.modes.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
              Language
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
              >
                {catalog.languages.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
              Title
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
                placeholder="Optional"
              />
            </label>
          </div>

          <div className="mb-3 grid grid-cols-2 gap-3">
            <MultiSelect
              label="Subject companies"
              options={catalog.tickers}
              value={subjCos}
              onChange={setSubjCos}
            />
            <MultiSelect
              label="Comparative companies"
              options={catalog.tickers}
              value={cmpCos}
              onChange={setCmpCos}
            />
            <MultiSelect
              label="Subject industries"
              options={catalog.industries}
              value={subjInds}
              onChange={setSubjInds}
            />
            <MultiSelect
              label="Comparative industries"
              options={catalog.industries}
              value={cmpInds}
              onChange={setCmpInds}
            />
          </div>

          <MultiSelect
            label="KPIs"
            options={catalog.kpis.map((k) => k.key)}
            value={kpis}
            onChange={setKpis}
          />
          <p className="mt-1 mb-3 text-[10px] text-slate-600">
            Labels:{" "}
            {catalog.kpis
              .filter((k) => kpis.includes(k.key))
              .map((k) => k.label)
              .join(", ") || "—"}
          </p>

          <div className="mb-4 flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => build(false)}
              className="rounded-md bg-indigo-500/20 px-3 py-1.5 text-xs text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-50"
            >
              Export prompt
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => build(true)}
              className="rounded-md border border-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-50"
            >
              Generate HTML
            </button>
          </div>
        </>
      )}

      {result?.ok && (
        <div className="space-y-2">
          <p className="text-[11px] text-emerald-400">Wrote artifacts to {result.dir}</p>
          {result.generate_error && (
            <p className="text-xs text-amber-400">{result.generate_error}</p>
          )}
          <pre className="max-h-80 overflow-auto rounded border border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-300 whitespace-pre-wrap">
            {result.prompt_markdown}
          </pre>
        </div>
      )}
    </div>
  );
}
