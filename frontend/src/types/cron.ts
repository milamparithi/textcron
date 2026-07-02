export interface TranslateRequest {
  text: string;
  timezone?: string;
}

export interface TranslateResponse {
  cron: string;
  text: string;
  explanation: string;
  warning?: string;
  trace_id?: string;
}

export interface ValidateRequest {
  cron: string;
}

export interface ValidateResponse {
  valid: boolean;
  explanation: string;
  next_times: string[];
}

export interface FeedbackRequest {
  trace_id: string;
  rating: "positive" | "negative";
  comment?: string;
}

export interface FeedbackResponse {
  id: string;
}
