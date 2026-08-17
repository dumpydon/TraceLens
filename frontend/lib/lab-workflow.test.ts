import { describe, expect, it } from "vitest";

import { deriveLabLifecycle, failedTrafficRequests } from "./lab-workflow";

describe("deriveLabLifecycle", () => {
  it("starts at scenario activation for the neutral baseline", () => {
    expect(deriveLabLifecycle({
      scenarioActive: false,
      trafficGenerated: false,
      investigationCreated: false,
    }).map((stage) => stage.state)).toEqual(["current", "future", "future", "future"]);
  });

  it("advances through active scenario, captured traffic, and investigation creation", () => {
    expect(deriveLabLifecycle({
      scenarioActive: true,
      trafficGenerated: false,
      investigationCreated: false,
    }).map((stage) => stage.state)).toEqual(["completed", "current", "future", "future"]);

    expect(deriveLabLifecycle({
      scenarioActive: true,
      trafficGenerated: true,
      investigationCreated: false,
    }).map((stage) => stage.state)).toEqual([
      "completed",
      "completed",
      "completed",
      "current",
    ]);

    expect(deriveLabLifecycle({
      scenarioActive: true,
      trafficGenerated: true,
      investigationCreated: true,
    }).every((stage) => stage.state === "completed")).toBe(true);
  });
});

describe("failedTrafficRequests", () => {
  it("counts only real failed response and connection outcomes", () => {
    expect(failedTrafficRequests({ "200": 8, "504": 3, connection_error: 1 })).toBe(4);
  });
});
