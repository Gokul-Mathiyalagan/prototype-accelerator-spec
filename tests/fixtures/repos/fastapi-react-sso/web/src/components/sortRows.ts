export type SortDirection = "asc" | "desc";

/** Sort rows by one column without changing the input. */
export function sortRows<T extends Record<string, string | number>>(
  rows: readonly T[],
  key: keyof T,
  direction: SortDirection,
): T[] {
  const sign = direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => (a[key] < b[key] ? -sign : a[key] > b[key] ? sign : 0));
}
