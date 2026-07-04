import { useState } from "react";
import { toast } from "sonner";

/** Monospaced, clickable cron expression badge — copies to clipboard on click. */
export default function CronBadge({ cron }: { cron: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(cron).then(() => {
      setCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <button
      onClick={handleCopy}
      className="group relative cursor-pointer rounded-lg border border-gray-200 bg-white px-4 py-3 font-mono text-lg tracking-wide text-gray-900 shadow-sm transition hover:border-blue-300 hover:shadow-md"
      aria-label="Copy cron expression"
    >
      <span>{cron}</span>
      <span className="ml-3 text-xs text-gray-400 transition group-hover:text-blue-500">
        {copied ? "Copied!" : "Copy"}
      </span>
    </button>
  );
}
