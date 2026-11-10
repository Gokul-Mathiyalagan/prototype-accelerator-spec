import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { space } from "../tokens/tokens";

export function PageShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ fontFamily: "var(--font-family)", fontSize: "var(--font-size-body)" }}>
      <header style={{ padding: space[3], borderBottom: "1px solid var(--color-border)" }}>
        <nav>
          <Link to="/">Team Insights</Link>
        </nav>
      </header>
      <main style={{ padding: space[4] }}>
        <h1 style={{ fontSize: "var(--font-size-heading)" }}>{title}</h1>
        {children}
      </main>
    </div>
  );
}
