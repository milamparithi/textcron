import type { TranslateResponse } from "../types/cron";
import CronBadge from "./CronBadge";
import NextTimes from "./NextTimes";
import FeedbackWidget from "./FeedbackWidget";

export default function ResultCard({
  result,
  nextTimes,
  onClear,
}: {
  result: TranslateResponse;
  nextTimes: string[];
  onClear: () => void;
}) {
  return (
    <div className="mt-6 animate-[fadeIn_0.3s_ease-out] space-y-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="space-y-1">
        <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
          Cron expression
        </p>
        <CronBadge cron={result.cron} />
      </div>

      <p className="text-gray-600">{result.explanation}</p>

      {result.warning && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
          {result.warning}
        </p>
      )}

      {nextTimes.length > 0 && <NextTimes times={nextTimes} />}

      <FeedbackWidget traceId={result.trace_id || ""} />

      <div className="flex gap-3 pt-1">
        <button
          onClick={onClear}
          className="cursor-pointer rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
        >
          Translate another
        </button>
      </div>
    </div>
  );
}
