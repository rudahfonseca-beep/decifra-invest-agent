import { useRef, type ReactNode } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

type Col<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
  /** CSS grid track for this column (default `minmax(0,1fr)`). */
  width?: string;
};

type Props<T> = {
  rows: T[];
  columns: Col<T>[];
  onRowClick?: (row: T) => void;
  empty?: string;
  /** Virtualize when row count exceeds this (default 80). */
  virtualThreshold?: number;
};

const ROW_H = 44;

export function DataTable<T>({
  rows,
  columns,
  onRowClick,
  empty,
  virtualThreshold = 80,
}: Props<T>) {
  const parentRef = useRef<HTMLDivElement>(null);
  const useVirtual = rows.length > virtualThreshold;
  const virtualizer = useVirtualizer({
    count: useVirtual ? rows.length : 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_H,
    overscan: 12,
  });

  const template = columns.map((c) => c.width || "minmax(0,1fr)").join(" ");

  const rowClass = `grid items-start border-b border-slate-800/80 text-slate-300 ${
    onRowClick ? "cursor-pointer hover:bg-slate-800/30" : "hover:bg-slate-800/20"
  }`;

  function cells(row: T) {
    return columns.map((c) => (
      <div key={c.key} role="cell" className={`min-w-0 px-2 py-2 ${c.className || ""}`}>
        {c.render(row)}
      </div>
    ));
  }

  return (
    <div ref={parentRef} role="table" className="min-h-0 flex-1 overflow-auto text-xs">
      <div
        role="row"
        className="sticky top-0 z-10 grid border-b border-slate-800 bg-[#0B1120]"
        style={{ gridTemplateColumns: template }}
      >
        {columns.map((c) => (
          <div
            key={c.key}
            role="columnheader"
            className={`px-2 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400 ${c.className || ""}`}
          >
            {c.header}
          </div>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="px-2 py-8 text-center text-xs italic text-slate-500">
          {empty || "No rows."}
        </div>
      ) : useVirtual ? (
        <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
          {virtualizer.getVirtualItems().map((vRow) => (
            <div
              key={vRow.key}
              role="row"
              data-index={vRow.index}
              ref={virtualizer.measureElement}
              className={`absolute left-0 top-0 w-full ${rowClass}`}
              style={{
                gridTemplateColumns: template,
                transform: `translateY(${vRow.start}px)`,
              }}
              onClick={onRowClick ? () => onRowClick(rows[vRow.index]) : undefined}
            >
              {cells(rows[vRow.index])}
            </div>
          ))}
        </div>
      ) : (
        <div>
          {rows.map((row, i) => (
            <div
              key={i}
              role="row"
              className={rowClass}
              style={{ gridTemplateColumns: template }}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {cells(row)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
