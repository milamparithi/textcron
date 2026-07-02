import { useState, useEffect } from "react";

type Props = {
  traceId: string;
};

const STORAGE_PREFIX = "tc_feedback_";

export default function FeedbackWidget({ traceId }: Props) {
  const storageKey = STORAGE_PREFIX + traceId;
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem(storageKey)) {
      setDone(true);
    }
  }, [storageKey]);

  if (!traceId) return null;

  if (done) {
    return (
      <p className="mt-4 border-t border-gray-100 pt-4 text-xs text-gray-400">
        Thanks for your feedback!
      </p>
    );
  }

  async function handleRate(value: "positive" | "negative") {
    if (sending) return;
    setSending(true);
    setError("");
    try {
      const payload: Record<string, unknown> = { trace_id: traceId, rating: value };
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail ?? "Request failed");
      }
      sessionStorage.setItem(storageKey, "1");
      setDone(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send feedback");
      setSending(false);
    }
  }

  return (
    <div className="mt-4 border-t border-gray-100 pt-4">
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-400">
        Was this helpful?
      </p>
      <div className="flex items-center gap-2">
        <button
          onClick={() => handleRate("positive")}
          disabled={sending}
          className={`cursor-pointer rounded-lg border px-3 py-1.5 text-lg transition disabled:opacity-40 ${
            done
              ? "border-green-400 bg-green-50 text-green-600"
              : "border-gray-300 text-gray-400 hover:bg-gray-100"
          }`}
        >
          &#x1F44D;
        </button>
        <button
          onClick={() => handleRate("negative")}
          disabled={sending}
          className={`cursor-pointer rounded-lg border px-3 py-1.5 text-lg transition disabled:opacity-40 ${
            done
              ? "border-red-400 bg-red-50 text-red-600"
              : "border-gray-300 text-gray-400 hover:bg-gray-100"
          }`}
        >
          &#x1F44E;
        </button>
      </div>
      {error && (
        <p className="mt-2 text-xs text-red-500">{error}</p>
      )}
    </div>
  );
}
