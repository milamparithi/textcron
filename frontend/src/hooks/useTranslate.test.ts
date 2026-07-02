import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTranslate } from "./useTranslate";

const mockTranslate = vi.fn();
const mockValidate = vi.fn();

vi.mock("../api/cron", () => ({
  translate: (...args: unknown[]) => mockTranslate(...args),
  validate: (...args: unknown[]) => mockValidate(...args),
}));

beforeEach(() => {
  mockTranslate.mockReset();
  mockValidate.mockReset();
});

describe("useTranslate", () => {
  it("starts with empty state", () => {
    const { result } = renderHook(() => useTranslate());
    expect(result.current.text).toBe("");
    expect(result.current.loading).toBe(false);
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("sets text via setText", () => {
    const { result } = renderHook(() => useTranslate());
    act(() => result.current.setText("every day"));
    expect(result.current.text).toBe("every day");
  });

  it("does nothing if text is empty", async () => {
    const { result } = renderHook(() => useTranslate());
    await act(() => result.current.handleSubmit());
    expect(mockTranslate).not.toHaveBeenCalled();
  });

  it("calls translate and validate on submit", async () => {
    mockTranslate.mockResolvedValue({ cron: "0 0 * * *", text: "daily", explanation: "Midnight" });
    mockValidate.mockResolvedValue({ valid: true, explanation: "ok", next_times: ["2026-01-01 00:00 UTC"] });

    const { result } = renderHook(() => useTranslate());
    act(() => result.current.setText("daily"));
    await act(() => result.current.handleSubmit());

    expect(mockTranslate).toHaveBeenCalledWith({ text: "daily" });
    expect(mockValidate).toHaveBeenCalledWith({ cron: "0 0 * * *" });
    expect(result.current.result?.cron).toBe("0 0 * * *");
    expect(result.current.nextTimes).toEqual(["2026-01-01 00:00 UTC"]);
    expect(result.current.error).toBeNull();
  });

  it("sets error on failure", async () => {
    mockTranslate.mockRejectedValue(new Error("LLM error"));

    const { result } = renderHook(() => useTranslate());
    act(() => result.current.setText("bad input"));
    await act(() => result.current.handleSubmit());

    expect(result.current.result).toBeNull();
    expect(result.current.error).toBe("LLM error");
  });

  it("clears state via handleClear", async () => {
    mockTranslate.mockResolvedValue({ cron: "0 0 * * *", text: "daily", explanation: "Midnight" });
    mockValidate.mockResolvedValue({ valid: true, explanation: "ok", next_times: [] });

    const { result } = renderHook(() => useTranslate());
    act(() => result.current.setText("daily"));
    await act(() => result.current.handleSubmit());

    act(() => result.current.handleClear());
    expect(result.current.text).toBe("");
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.nextTimes).toEqual([]);
  });
});
