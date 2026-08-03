import { Bell, Search } from "lucide-react";

export type UniverseScope = "core" | "all";

type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  scope: UniverseScope;
  onScopeChange: (scope: UniverseScope) => void;
};

export function Header({ query, onQueryChange, scope, onScopeChange }: Props) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-800 bg-slate-900/80 px-4 backdrop-blur-sm">
      <div className="relative flex-1 max-w-xl">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
        <input
          type="search"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search CNPJ, ticker, ISIN…"
          className="w-full rounded-md border border-slate-800 bg-slate-950/60 py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder:text-slate-600 outline-none focus:border-indigo-400/50 focus:ring-1 focus:ring-indigo-400/30"
        />
      </div>
      <div
        className="flex shrink-0 rounded-md border border-slate-800 p-0.5 text-[10px]"
        role="group"
        aria-label="Universe scope"
      >
        {(
          [
            ["core", "Core"],
            ["all", "All B3"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => onScopeChange(id)}
            className={`rounded px-2.5 py-1 font-medium transition ${
              scope === id
                ? "bg-indigo-600 text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
            title={
              id === "core"
                ? "Ibovespa ∪ watchlist (fast research set)"
                : "All listed equities in equities.json"
            }
          >
            {label}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="relative rounded-md border border-slate-800 p-2 text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-indigo-400" />
      </button>
    </header>
  );
}
