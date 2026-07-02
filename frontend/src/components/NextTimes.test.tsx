import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import NextTimes from "./NextTimes";

describe("NextTimes", () => {
  it("renders times list", () => {
    render(<NextTimes times={["2026-01-01 15:00 UTC", "2026-01-02 15:00 UTC"]} />);
    expect(screen.getByText("2026-01-01 15:00 UTC")).toBeInTheDocument();
    expect(screen.getByText("2026-01-02 15:00 UTC")).toBeInTheDocument();
  });

  it("renders heading", () => {
    render(<NextTimes times={[]} />);
    expect(screen.getByText("Next runs")).toBeInTheDocument();
  });
});
