import { TrendingUp } from "lucide-react";
import { CatalystCard } from "./CatalystCard";
import type { CatalystItem } from "../types";

type Props = {
  items: CatalystItem[];
  loading?: boolean;
  refreshing?: boolean;
};

export function CatalystFeed({ items, loading, refreshing }: Props) {
  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-l border-slate-800 bg-slate-900">
      <div className="flex h-14 shrink-0 items-center gap-2 border-b border-slate-800 px-3">
        <TrendingUp className="h-3.5 w-3.5 text-indigo-400" />
        <div>
          <div className="text-xs font-medium text-slate-100">Action Catalyst Feed</div>
          <div className="text-[10px] text-slate-500">
            Cross-asset impact timeline
            {refreshing ? " · refreshing…" : ""}
          </div>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading && items.length === 0 && (
          <p className="px-3 py-4 text-xs italic text-slate-500">Loading…</p>
        )}
        {!loading && items.length === 0 && (
          <p className="px-3 py-4 text-xs italic text-slate-500">No catalysts.</p>
        )}
        {items.map((item) => (
          <CatalystCard key={item.id} item={item} />
        ))}
      </div>
    </aside>
  );
}
