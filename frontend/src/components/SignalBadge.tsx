import type { Signal } from "../types";

const STYLES: Record<Signal, string> = {
  safe: "bg-emerald-500/10 text-emerald-400",
  warning: "bg-amber-500/10 text-amber-400",
  distress: "bg-rose-500/10 text-rose-400",
};

const LABELS: Record<Signal, string> = {
  safe: "Safe",
  warning: "Watch",
  distress: "Distress",
};

type Props = {
  signal: Signal;
  label?: string;
};

export function SignalBadge({ signal, label }: Props) {
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium tracking-wide ${STYLES[signal]}`}
    >
      {label ?? LABELS[signal]}
    </span>
  );
}
