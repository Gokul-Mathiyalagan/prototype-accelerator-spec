import { Link } from "react-router-dom";
import { PageShell } from "../components";

export function Home() {
  return (
    <PageShell title="Team Insights">
      <p>
        <Link to="/login">Sign in</Link> to see your team.
      </p>
    </PageShell>
  );
}
