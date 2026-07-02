import type {
  TranslateRequest,
  TranslateResponse,
  ValidateRequest,
  ValidateResponse,
  FeedbackRequest,
  FeedbackResponse,
} from "../types/cron";

const BASE = "/api";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export function translate(data: TranslateRequest) {
  return post<TranslateResponse>("/translate", data);
}

export function validate(data: ValidateRequest) {
  return post<ValidateResponse>("/validate", data);
}

export function submitFeedback(data: FeedbackRequest) {
  return post<FeedbackResponse>("/feedback", data);
}
