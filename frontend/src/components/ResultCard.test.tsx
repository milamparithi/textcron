import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ResultCard from "./ResultCard";

const baseResult = {
  cron: "0 15 * * 1-5",
  text: "weekdays at 3pm",
  explanation: "At 3:00 PM, Monday through Friday",
};

describe("ResultCard", () => {
  it("renders cron, explanation, and next times", () => {
    render(<ResultCard result={baseResult} nextTimes={["2026-01-01 15:00 UTC"]} onClear={vi.fn()} />);
    expect(screen.getByText("0 15 * * 1-5")).toBeInTheDocument();
    expect(screen.getByText("At 3:00 PM, Monday through Friday")).toBeInTheDocument();
    expect(screen.getByText("2026-01-01 15:00 UTC")).toBeInTheDocument();
  });

  it("shows warning when present", () => {
    const result = { ...baseResult, warning: "Runs very frequently" };
    render(<ResultCard result={result} nextTimes={[]} onClear={vi.fn()} />);
    expect(screen.getByText("Runs very frequently")).toBeInTheDocument();
  });

  it("shows translate another button", () => {
    render(<ResultCard result={baseResult} nextTimes={[]} onClear={vi.fn()} />);
    expect(screen.getByText("Translate another")).toBeInTheDocument();
  });

  it("calls onClear on button click", () => {
    const onClear = vi.fn();
    render(<ResultCard result={baseResult} nextTimes={[]} onClear={onClear} />);
    screen.getByText("Translate another").click();
    expect(onClear).toHaveBeenCalled();
  });
});
