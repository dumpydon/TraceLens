import { describe, expect, it } from "vitest";

import { incidentPresentationForScenario } from "./incident-presentation";

describe("incidentPresentationForScenario", () => {
  it.each([
    [
      "payment_latency",
      "Checkout timeouts with delayed payment responses",
      "Repeated checkout 504s observed while matching payment requests complete beyond the checkout timeout budget.",
    ],
    [
      "payment_failure",
      "Checkout failures with upstream payment errors",
      "Repeated checkout failures observed alongside matching payment-service rejection responses.",
    ],
    [
      "bad_deployment",
      "Checkout failures following a payment deployment",
      "Elevated checkout errors observed after a recent payment-service deployment change.",
    ],
    [
      "connection_exhaustion",
      "Checkout failures with payment-service unavailability",
      "Checkout requests are failing while the payment service reports depleted provider connections.",
    ],
    [
      "baseline",
      "Checkout reliability baseline",
      "Normal checkout and payment behavior observed with successful requests and low latency.",
    ],
  ])("maps %s to observable incident copy", (scenario, title, summary) => {
    expect(incidentPresentationForScenario(scenario)).toEqual({ title, summary });
  });

  it("uses safe generic copy for unknown control-layer scenarios", () => {
    expect(incidentPresentationForScenario("future_scenario")).toEqual({
      title: "Checkout reliability degradation",
      summary: "Elevated checkout failures observed in the Incident Lab.",
    });
  });
});
