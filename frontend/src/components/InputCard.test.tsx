import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import InputCard from "./InputCard";

describe("InputCard", () => {
  it("renders textarea and button", () => {
    render(<InputCard value="" onChange={vi.fn()} onSubmit={vi.fn()} loading={false} />);
    expect(screen.getByPlaceholderText(/every weekday/)).toBeInTheDocument();
    expect(screen.getByText("Translate")).toBeInTheDocument();
  });

  it("calls onChange on input", () => {
    const onChange = vi.fn();
    render(<InputCard value="" onChange={onChange} onSubmit={vi.fn()} loading={false} />);
    fireEvent.change(screen.getByPlaceholderText(/every weekday/), { target: { value: "daily" } });
    expect(onChange).toHaveBeenCalledWith("daily");
  });

  it("calls onSubmit on Enter without Shift", () => {
    const onSubmit = vi.fn();
    render(<InputCard value="daily" onChange={vi.fn()} onSubmit={onSubmit} loading={false} />);
    fireEvent.keyDown(screen.getByPlaceholderText(/every weekday/), { key: "Enter", shiftKey: false });
    expect(onSubmit).toHaveBeenCalled();
  });

  it("does not call onSubmit on Shift+Enter", () => {
    const onSubmit = vi.fn();
    render(<InputCard value="daily" onChange={vi.fn()} onSubmit={onSubmit} loading={false} />);
    fireEvent.keyDown(screen.getByPlaceholderText(/every weekday/), { key: "Enter", shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables button when loading", () => {
    render(<InputCard value="daily" onChange={vi.fn()} onSubmit={vi.fn()} loading={true} />);
    expect(screen.getByText("Translating...")).toBeInTheDocument();
  });

  it("disables button when value is empty", () => {
    render(<InputCard value="" onChange={vi.fn()} onSubmit={vi.fn()} loading={false} />);
    expect(screen.getByText("Translate")).toBeDisabled();
  });
});
