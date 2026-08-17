import { describe, expect, it } from "vitest";
import { deriveInvestigationProgress, formatPercent, formatRelativeTime } from "./format";

describe("format helpers", () => {
  it("formats relative minutes deterministically", () => {
    expect(formatRelativeTime("2026-08-15T10:00:00Z", Date.parse("2026-08-15T10:05:00Z"))).toBe("5m ago");
  });
  it("labels model scores as percentages", () => expect(formatPercent(0.875)).toBe("88%"));
  it("derives completed and current steps from real investigation events", () => {
    const progress = deriveInvestigationProgress([
      "investigation_started",
      "context_collection_started",
      "deployment_found",
      "runtime_analysis_completed",
      "retrieval_started",
    ], "investigating");
    expect(progress.completedSteps).toEqual([true, true, true, false, false, false, false]);
    expect(progress.currentIndex).toBe(3);
    expect(progress.percentage).toBe(43);
  });

  it("keeps completed stages while a refinement loops back to retrieval", () => {
    const progress = deriveInvestigationProgress([
      "context_collection_started",
      "deployment_found",
      "runtime_analysis_completed",
      "documents_retrieved",
      "hypothesis_generated",
      "verification_completed",
      "investigation_refined",
    ], "investigating");
    expect(progress.currentIndex).toBe(3);
    expect(progress.completedSteps.slice(0, 6)).toEqual([true, true, true, true, true, true]);
    expect(progress.percentage).toBe(86);
  });

  it("marks every step complete for a resolved investigation", () => {
    const progress = deriveInvestigationProgress([], "resolved");
    expect(progress.completedSteps.every(Boolean)).toBe(true);
    expect(progress.currentIndex).toBeNull();
    expect(progress.percentage).toBe(100);
  });
});
