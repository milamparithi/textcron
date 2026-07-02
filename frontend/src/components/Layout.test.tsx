import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Layout from "./Layout";

describe("Layout", () => {
  it("renders children and footer", () => {
    render(<Layout><p>hello</p></Layout>);
    expect(screen.getByText("hello")).toBeInTheDocument();
    expect(screen.getByText(/TextCron/)).toBeInTheDocument();
  });
});
