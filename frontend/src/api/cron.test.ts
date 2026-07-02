import { describe, it, expect, vi, beforeEach } from "vitest";
import { translate, validate } from "./cron";

function mockFetch(status: number, body: unknown) {
  return vi.mocked(fetch).mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
  } as Response);
}

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockReset();
});

describe("translate", () => {
  it("returns response on success", async () => {
    mockFetch(200, { cron: "0 15 * * 1-5", text: "weekdays at 3pm", explanation: "test" });
    const res = await translate({ text: "weekdays at 3pm" });
    expect(res.cron).toBe("0 15 * * 1-5");
  });

  it("throws on error response", async () => {
    mockFetch(400, { detail: "Bad input" });
    await expect(translate({ text: "bad" })).rejects.toThrow("Bad input");
  });
});

describe("validate", () => {
  it("returns next times on success", async () => {
    mockFetch(200, { valid: true, explanation: "ok", next_times: ["2026-01-01 00:00 UTC"] });
    const res = await validate({ cron: "0 0 * * *" });
    expect(res.next_times).toHaveLength(1);
  });

  it("throws on error response", async () => {
    mockFetch(500, { detail: "Server error" });
    await expect(validate({ cron: "bad" })).rejects.toThrow("Server error");
  });
});
