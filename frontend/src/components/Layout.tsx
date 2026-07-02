import type { ReactNode } from "react";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto flex min-h-dvh max-w-xl flex-col px-4 py-8 sm:py-16">
      <main className="flex-1">{children}</main>
      <footer className="mt-12 text-center text-sm text-gray-400">
        TextCron &mdash; natural language to cron schedule
      </footer>
    </div>
  );
}
