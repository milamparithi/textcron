import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import HomePage from "./HomePage";

function createMockState() {
  return {
    text: "",
    setText: vi.fn(),
    loading: false,
    result: null as {
      cron: string;
      text: string;
      explanation: string;
      warning?: string;
    } | null,
    nextTimes: [] as string[],
    error: null as string | null,
    handleSubmit: vi.fn(),
    handleClear: vi.fn(),
  };
}

const mockState = createMockState();

vi.mock("../hooks/useTranslate", () => ({
  useTranslate: () => mockState,
}));

beforeEach(() => {
  Object.assign(mockState, createMockState());
});

describe("HomePage", () => {
  it("renders header and input", () => {
    render(<HomePage />);
    expect(screen.getByText("TextCron")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/every weekday/)).toBeInTheDocument();
  });

  it("shows ResultCard when result is present", () => {
    mockState.result = { cron: "0 0 * * *", text: "daily", explanation: "Midnight" };
    mockState.nextTimes = ["2026-01-01 00:00 UTC"];
    render(<HomePage />);
    expect(screen.getByText("0 0 * * *")).toBeInTheDocument();
  });

  it("shows ErrorCard when error is present", () => {
    mockState.error = "Something went wrong";
    render(<HomePage />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Try again")).toBeInTheDocument();
  });
});
