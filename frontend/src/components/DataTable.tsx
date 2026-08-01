import type { ReactNode } from "react";

type Col<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
};

type Props<T> = {
  rows: T[];
  columns: Col<T>[];
  onRowClick?: (row: T) => void;
  empty?: string;
};

export function DataTable<T>({ rows, columns, onRowClick, empty }: Props<T>) {
  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <table className="w-full border-collapse text-xs">
        <thead className="sticky top-0 z-10 bg-[#0B1120]">
          <tr className="border-b border-slate-800">
            {columns.map((c) => (
              <th
                key={c.key}
                className={`px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400 ${c.className || ""}`}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className={`border-b border-slate-800/80 text-slate-300 ${
                onRowClick ? "cursor-pointer hover:bg-slate-800/30" : "hover:bg-slate-800/20"
              }`}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((c) => (
                <td key={c.key} className={`px-2 py-2 align-top ${c.className || ""}`}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="px-2 py-8 text-center text-xs italic text-slate-500"
              >
                {empty || "No rows."}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
