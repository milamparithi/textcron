import { useState } from "react";
import { translate, validate } from "../api/cron";
import type { TranslateResponse } from "../types/cron";

/** State machine hook managing translate flow: text input, loading, result, next times, error. */
export function useTranslate() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TranslateResponse | null>(null);
  const [nextTimes, setNextTimes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setNextTimes([]);

    try {
      const res = await translate({ text: text.trim() });
      setResult(res);

      const val = await validate({ cron: res.cron });
      setNextTimes(val.next_times);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setText("");
    setResult(null);
    setNextTimes([]);
    setError(null);
  }

  return { text, setText, loading, result, nextTimes, error, handleSubmit, handleClear };
}
