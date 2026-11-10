import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiRequestError, apiGet, type Member, type Page } from "../api/client";
import { DataTable, PageShell, type Column } from "../components";

const columns: Column<Member>[] = [
  { key: "name", label: "Name" },
  { key: "role", label: "Role" },
  { key: "start_date", label: "Start date" },
];

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "no-access" }
  | { kind: "ready"; members: Member[] };

export function TeamDashboard() {
  const { id } = useParams();
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    apiGet<Page<Member>>(`/teams/${id}/members`)
      .then((page) => setState({ kind: "ready", members: page.items }))
      .catch((error: unknown) => {
        if (error instanceof ApiRequestError && error.status === 403) setState({ kind: "no-access" });
        else setState({ kind: "error", message: error instanceof Error ? error.message : "Something went wrong." });
      });
  }, [id]);

  return (
    <PageShell title="Team dashboard">
      {state.kind === "loading" && <p>Loading…</p>}
      {state.kind === "error" && <p role="alert">{state.message}</p>}
      {state.kind === "no-access" && <p>You don't have access to this team.</p>}
      {state.kind === "ready" && <DataTable columns={columns} rows={state.members} emptyMessage="No members yet." />}
      <a href={`/api/v1/teams/${id}/members.csv`}>Export CSV</a>
    </PageShell>
  );
}
