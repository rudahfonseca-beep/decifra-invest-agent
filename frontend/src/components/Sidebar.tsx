import {
  Activity,
  BarChart3,
  Building2,
  ClipboardList,
  Factory,
  FileText,
  LayoutGrid,
  LineChart,
  List,
  Shield,
  Waves,
} from "lucide-react";
import type { ViewId } from "../types";

const NAV: { id: ViewId; label: string; icon: typeof LayoutGrid }[] = [
  { id: "screener", label: "Opportunity Screener", icon: LayoutGrid },
  { id: "industries", label: "Industries", icon: Factory },
  { id: "tickers", label: "Tickers", icon: List },
  { id: "credit", label: "Credit overview", icon: BarChart3 },
  { id: "detail", label: "Company detail", icon: Building2 },
  { id: "valuation", label: "Valuation", icon: LineChart },
  { id: "report", label: "Report builder", icon: FileText },
  { id: "coverage", label: "Data coverage", icon: ClipboardList },
  { id: "profile", label: "Schema · Profile", icon: Building2 },
  { id: "debt", label: "Schema · Credit & Debt", icon: Shield },
  { id: "waterfall", label: "Schema · Waterfall", icon: Waves },
];

type Props = {
  active: ViewId;
  onNavigate: (id: ViewId) => void;
};

export function Sidebar({ active, onNavigate }: Props) {
  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-4 py-4">
        <div className="text-sm font-semibold tracking-tight text-slate-100">decifra</div>
        <div className="mt-0.5 text-[11px] text-indigo-400">Unified Capital Analyst</div>
      </div>

      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-3">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
        </span>
        <div>
          <div className="text-[11px] font-medium text-slate-200">Pipeline live</div>
          <div className="flex items-center gap-1 text-[10px] text-slate-500">
            <Activity className="h-3 w-3" />
            CVM · ANBIMA · B3
          </div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2">
        {NAV.map(({ id, label, icon: Icon }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate(id)}
              className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-left text-xs transition-colors ${
                isActive
                  ? "bg-slate-800/80 text-indigo-400"
                  : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
              }`}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 px-4 py-3 text-[10px] text-slate-600">
        Streamlit parity · research-grade
      </div>
    </aside>
  );
}
