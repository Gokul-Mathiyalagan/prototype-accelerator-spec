const KEY = "team-insights.token";

export function getToken(): string | null {
  return sessionStorage.getItem(KEY);
}

export async function signIn(username: string): Promise<void> {
  const reply = await fetch("/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  if (!reply.ok) throw new Error("Sign-in failed");
  const body = (await reply.json()) as { access_token: string };
  sessionStorage.setItem(KEY, body.access_token);
}
