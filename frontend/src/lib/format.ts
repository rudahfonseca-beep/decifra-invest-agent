export function fmtNum(value: number | string | null | undefined, digits = 1): string {
  if (value == null || value === "") return "—";
  if (typeof value === "string") return value;
  if (Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${fmtNum(value, digits)}%`;
}

export function fmtRatio(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${fmtNum(value, digits)}x`;
}

export function fmtScore(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return fmtNum(value, 1);
}

export function fmtMetric(
  value: number | null | undefined,
  pct: boolean
): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (pct) return `${fmtNum(value * 100, 1)}%`;
  if (Math.abs(value) >= 1000) return fmtNum(value, 0);
  return fmtNum(value, 2);
}
