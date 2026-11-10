import { describe, expect, it } from "vitest";
import { sortRows } from "./sortRows";

const rows = [
  { name: "Marcus", start_date: "2024-09-16" },
  { name: "Ana", start_date: "2021-01-11" },
];

describe("sortRows", () => {
  it("sorts ascending and descending", () => {
    expect(sortRows(rows, "name", "asc").map((r) => r.name)).toEqual(["Ana", "Marcus"]);
    expect(sortRows(rows, "start_date", "desc").map((r) => r.name)).toEqual(["Marcus", "Ana"]);
  });

  it("leaves the input unchanged", () => {
    sortRows(rows, "name", "asc");
    expect(rows[0].name).toBe("Marcus");
  });
});
