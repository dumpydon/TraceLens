import { describe, expect, it } from "vitest";
import { formatPercent, formatRelativeTime, stageIndex } from "./format";

describe("format helpers", () => {
  it("formats relative minutes deterministically", () => {
    expect(formatRelativeTime("2026-08-15T10:00:00Z", Date.parse("2026-08-15T10:05:00Z"))).toBe("5m ago");
  });
  it("labels model scores as percentages", () => expect(formatPercent(0.875)).toBe("88%"));
  it("maps graph stages to progress positions", () => expect(stageIndex("verify")).toBe(4));
});

