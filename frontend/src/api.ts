import type {
  Integration,
  PublishResponse,
  ReviewRequest,
  ReviewResponse,
  Scenario,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  scenarios: () => request<Scenario[]>("/api/scenarios"),
  integrations: () => request<Integration[]>("/api/integrations"),
  createReview: (payload: ReviewRequest) =>
    request<ReviewResponse>("/api/reviews", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  publishReview: (reviewId: string) =>
    request<PublishResponse>(`/api/reviews/${reviewId}/publish`, { method: "POST" }),
};
