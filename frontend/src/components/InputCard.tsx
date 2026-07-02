import { useRef } from "react";

export default function InputCard({
  value,
  onChange,
  onSubmit,
  loading,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    onChange(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading && value.trim()) onSubmit();
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-6">
      <label htmlFor="nl-input" className="sr-only">
        Describe your schedule
      </label>
      <textarea
        id="nl-input"
        ref={textareaRef}
        rows={2}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="e.g. every weekday at 3pm"
        disabled={loading}
        className="min-h-[3rem] w-full resize-none text-base outline-none placeholder:text-gray-400 disabled:opacity-50"
      />
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-gray-400">Press Enter to submit</p>
        <button
          onClick={onSubmit}
          disabled={loading || !value.trim()}
          className="flex cursor-pointer items-center justify-center rounded-lg bg-gray-900 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg
                className="h-4 w-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
              Translating...
            </span>
          ) : (
            "Translate"
          )}
        </button>
      </div>
    </div>
  );
}
