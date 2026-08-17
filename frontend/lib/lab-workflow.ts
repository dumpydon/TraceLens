export type LabLifecycleState = "completed" | "current" | "future";

export interface LabLifecycleStage {
  label: string;
  state: LabLifecycleState;
}

export function deriveLabLifecycle({
  scenarioActive,
  trafficGenerated,
  investigationCreated,
}: {
  scenarioActive: boolean;
  trafficGenerated: boolean;
  investigationCreated: boolean;
}): LabLifecycleStage[] {
  const currentIndex = investigationCreated ? 4 : trafficGenerated ? 3 : scenarioActive ? 1 : 0;
  const labels = [
    scenarioActive || trafficGenerated ? "Scenario active" : "Activate scenario",
    trafficGenerated ? "Traffic generated" : "Generate traffic",
    trafficGenerated ? "Evidence captured" : "Capture evidence",
    investigationCreated ? "Investigation created" : trafficGenerated ? "Create investigation" : "Investigate",
  ];

  return labels.map((label, index) => ({
    label,
    state:
      currentIndex === 4 || index < currentIndex
        ? "completed"
        : index === currentIndex
          ? "current"
          : "future",
  }));
}

export function failedTrafficRequests(results: Record<string, number>): number {
  return Object.entries(results).reduce((total, [outcome, count]) => {
    const status = Number(outcome);
    return total + (outcome === "connection_error" || status >= 400 ? count : 0);
  }, 0);
}
