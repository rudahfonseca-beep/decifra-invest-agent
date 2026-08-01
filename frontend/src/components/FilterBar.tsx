import type { FilterState } from "../types";

type Props = {
  filters: FilterState;
  industries: string[];
  cohorts: string[];
  onChange: (next: FilterState) => void;
  onRefresh?: () => void;
};

export function FilterBar({ filters, industries, cohorts, onChange, onRefresh }: Props) {
  return (
    <div className="mb-3 flex flex-wrap items-end gap-3 rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2.5">
      <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
        Industry
        <select
          value={filters.industry}
          onChange={(e) => onChange({ ...filters, industry: e.target.value })}
          className="min-w-[10rem] rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-400/50"
        >
          {(industries.length ? industries : ["All"]).map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
        Cohort
        <select
          value={filters.cohort}
          onChange={(e) => onChange({ ...filters, cohort: e.target.value })}
          className="min-w-[8rem] rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-400/50"
        >
          {(cohorts.length ? cohorts : ["All"]).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-2 pb-1.5 text-xs text-slate-400">
        <input
          type="checkbox"
          checked={filters.includeSignals}
          onChange={(e) => onChange({ ...filters, includeSignals: e.target.checked })}
          className="rounded border-slate-700"
        />
        Qualitative signals
      </label>
      <label className="flex items-center gap-2 pb-1.5 text-xs text-slate-400">
        <input
          type="checkbox"
          checked={filters.showIncomplete}
          onChange={(e) => onChange({ ...filters, showIncomplete: e.target.checked })}
          className="rounded border-slate-700"
        />
        Show incomplete
      </label>
      {onRefresh && (
        <button
          type="button"
          onClick={onRefresh}
          className="ml-auto rounded-md border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-xs text-indigo-400 hover:bg-slate-800"
        >
          Refresh scores
        </button>
      )}
    </div>
  );
}
