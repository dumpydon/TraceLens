export interface IncidentPresentation {
  title: string;
  summary: string;
}

const SCENARIO_PRESENTATIONS: Record<string, IncidentPresentation> = {
  payment_latency: {
    title: "Checkout timeouts with delayed payment responses",
    summary:
      "Repeated checkout 504s observed while matching payment requests complete beyond the checkout timeout budget.",
  },
  payment_failure: {
    title: "Checkout failures with upstream payment errors",
    summary:
      "Repeated checkout failures observed alongside matching payment-service rejection responses.",
  },
  bad_deployment: {
    title: "Checkout failures following a payment deployment",
    summary:
      "Elevated checkout errors observed after a recent payment-service deployment change.",
  },
  connection_exhaustion: {
    title: "Checkout failures with payment-service unavailability",
    summary:
      "Checkout requests are failing while the payment service reports depleted provider connections.",
  },
  baseline: {
    title: "Checkout reliability baseline",
    summary:
      "Normal checkout and payment behavior observed with successful requests and low latency.",
  },
};

const DEFAULT_PRESENTATION: IncidentPresentation = {
  title: "Checkout reliability degradation",
  summary: "Elevated checkout failures observed in the Incident Lab.",
};

export function incidentPresentationForScenario(
  scenarioName: string | null | undefined,
): IncidentPresentation {
  return SCENARIO_PRESENTATIONS[scenarioName ?? ""] ?? DEFAULT_PRESENTATION;
}
