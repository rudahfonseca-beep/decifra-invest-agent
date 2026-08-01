import { LineageHint } from "./LineageHint";

type Props = {
  value: string;
  lineage?: string | null;
  tone?: "default" | "safe" | "warning" | "distress";
};

const TONE: Record<NonNullable<Props["tone"]>, string> = {
  default: "text-slate-100",
  safe: "text-emerald-400",
  warning: "text-amber-400",
  distress: "text-rose-400",
};

export function MetricCell({ value, lineage, tone = "default" }: Props) {
  return (
    <div>
      <div className={`tabular-nums ${TONE[tone]}`}>{value}</div>
      <LineageHint text={lineage} />
    </div>
  );
}
