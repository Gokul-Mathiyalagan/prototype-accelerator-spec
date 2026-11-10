import { useState } from "react";
import { color, space } from "../tokens/tokens";
import { sortRows, type SortDirection } from "./sortRows";

export type Column<T> = { key: keyof T & string; label: string };

type Props<T extends Record<string, string | number>> = {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
};

export function DataTable<T extends Record<string, string | number>>({ columns, rows, emptyMessage = "Nothing to show." }: Props<T>) {
  const [sort, setSort] = useState<{ key: keyof T; direction: SortDirection } | null>(null);
  if (rows.length === 0) return <p style={{ color: color.muted }}>{emptyMessage}</p>;
  const shown = sort ? sortRows(rows, sort.key, sort.direction) : rows;
  return (
    <table style={{ borderCollapse: "collapse", width: "100%" }}>
      <thead>
        <tr>
          {columns.map((c) => (
            <th
              key={c.key}
              onClick={() => setSort({ key: c.key, direction: sort?.direction === "asc" ? "desc" : "asc" })}
              style={{ textAlign: "left", padding: space[2], borderBottom: `1px solid ${color.border}` }}
            >
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {shown.map((row, i) => (
          <tr key={i}>
            {columns.map((c) => (
              <td key={c.key} style={{ padding: space[2] }}>{row[c.key]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
