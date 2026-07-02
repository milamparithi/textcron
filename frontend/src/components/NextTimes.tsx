export default function NextTimes({ times }: { times: string[] }) {
  return (
    <div>
      <p className="mb-1 text-sm font-medium text-gray-500">Next runs</p>
      <ul className="space-y-0.5">
        {times.map((t, i) => (
          <li key={i} className="font-mono text-sm text-gray-700">
            {t}
          </li>
        ))}
      </ul>
    </div>
  );
}
