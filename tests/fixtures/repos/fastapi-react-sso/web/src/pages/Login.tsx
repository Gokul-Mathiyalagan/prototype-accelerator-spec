import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { signIn } from "../auth";
import { Button, PageShell } from "../components";

export function Login() {
  const [username, setUsername] = useState("alice");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  return (
    <PageShell title="Sign in">
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          try {
            await signIn(username);
            navigate("/teams/1");
          } catch {
            setError("Sign-in failed. Try alice or bob.");
          }
        }}
      >
        <label htmlFor="username">User name</label>
        <input id="username" required value={username} onChange={(e) => setUsername(e.target.value)} />
        <Button type="submit">Sign in</Button>
        {error && <p role="alert">{error}</p>}
      </form>
    </PageShell>
  );
}
