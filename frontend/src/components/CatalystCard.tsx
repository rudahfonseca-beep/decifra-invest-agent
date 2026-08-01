import { SignalBadge } from "./SignalBadge";
import type { CatalystItem } from "../types";

type Props = {
  item: CatalystItem;
};

export function CatalystCard({ item }: Props) {
  return (
    <article className="border-b border-slate-800 px-3 py-3 last:border-b-0">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
          {item.source}
        </span>
        <span className="text-[10px] text-slate-600">{item.ts_relative}</span>
      </div>
      <h3 className="text-xs font-medium leading-snug text-slate-100">{item.title}</h3>
      <p className="mt-1 text-[11px] leading-relaxed text-slate-400">{item.impact}</p>
      <div className="mt-2">
        <SignalBadge signal={item.signal} />
      </div>
    </article>
  );
}
