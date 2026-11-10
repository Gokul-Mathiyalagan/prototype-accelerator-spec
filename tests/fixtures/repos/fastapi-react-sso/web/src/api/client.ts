import { getToken } from "../auth";

export type ApiError = { code: string; message: string; request_id: string };

export class ApiRequestError extends Error {
  constructor(public status: number, public error: ApiError) {
    super(error.message);
  }
}

/** GET a JSON resource with the signed-in user's bearer token. */
export async function apiGet<T>(path: string): Promise<T> {
  const reply = await fetch(`/api/v1${path}`, {
    headers: { Authorization: `Bearer ${getToken() ?? ""}` },
  });
  if (!reply.ok) {
    const body = (await reply.json()) as { error: ApiError };
    throw new ApiRequestError(reply.status, body.error);
  }
  return (await reply.json()) as T;
}

export type Member = { name: string; role: string; start_date: string };
export type Page<T> = { items: T[]; page: number; page_size: number; total: number };
