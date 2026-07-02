import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import CronBadge from "./CronBadge";

beforeEach(() => {
  vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn() } });
  vi.stubGlobal("setTimeout", vi.fn());
});

describe("CronBadge", () => {
  it("renders the cron expression", () => {
    render(<CronBadge cron="0 15 * * 1-5" />);
    expect(screen.getByText("0 15 * * 1-5")).toBeInTheDocument();
  });

  it("renders copy label", () => {
    render(<CronBadge cron="* * * * *" />);
    expect(screen.getByText("Copy")).toBeInTheDocument();
  });
});
