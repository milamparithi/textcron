export default function ErrorCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="mt-6 animate-[fadeIn_0.3s_ease-out] rounded-xl border border-red-200 bg-red-50 p-6 text-center">
      <p className="text-red-700">{message}</p>
      <button
        onClick={onRetry}
        className="mt-4 cursor-pointer rounded-lg bg-red-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-red-700"
      >
        Try again
      </button>
    </div>
  );
}
