import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorCard from "./ErrorCard";

describe("ErrorCard", () => {
  it("renders message and retry button", () => {
    render(<ErrorCard message="Something broke" onRetry={vi.fn()} />);
    expect(screen.getByText("Something broke")).toBeInTheDocument();
    expect(screen.getByText("Try again")).toBeInTheDocument();
  });

  it("calls onRetry on button click", () => {
    const onRetry = vi.fn();
    render(<ErrorCard message="err" onRetry={onRetry} />);
    screen.getByText("Try again").click();
    expect(onRetry).toHaveBeenCalled();
  });
});
