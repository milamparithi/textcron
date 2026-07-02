import { useTranslate } from "../hooks/useTranslate";
import InputCard from "../components/InputCard";
import ResultCard from "../components/ResultCard";
import ErrorCard from "../components/ErrorCard";

export default function HomePage() {
  const { text, setText, loading, result, nextTimes, error, handleSubmit, handleClear } =
    useTranslate();

  return (
    <div className="space-y-8">
      <header className="text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          TextCron
        </h1>
        <p className="mt-2 text-gray-500">
          Describe your schedule in plain English
        </p>
      </header>

      <InputCard
        value={text}
        onChange={setText}
        onSubmit={handleSubmit}
        loading={loading}
      />

      {result && (
        <ResultCard
          result={result}
          nextTimes={nextTimes}
          onClear={handleClear}
        />
      )}

      {error && <ErrorCard message={error} onRetry={handleSubmit} />}
    </div>
  );
}
