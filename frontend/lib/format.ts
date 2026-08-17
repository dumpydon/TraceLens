export function formatRelativeTime(value: string, now = Date.now()): string {
  const deltaSeconds = Math.max(0, Math.floor((now - new Date(value).getTime()) / 1000));
  if (deltaSeconds < 60) return `${deltaSeconds}s ago`;
  const minutes = Math.floor(deltaSeconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export const workflowStages = [
  { key: "load", label: "Load Incident" },
  { key: "context", label: "Collect Context" },
  { key: "runtime", label: "Analyze Runtime" },
  { key: "retrieval", label: "Retrieve Knowledge" },
  { key: "hypothesis", label: "Form Hypothesis" },
  { key: "verify", label: "Verify Hypothesis" },
  { key: "report", label: "Generate Report" },
] as const;

export interface InvestigationProgress {
  completedSteps: boolean[];
  currentIndex: number | null;
  failedIndex: number | null;
  percentage: number | null;
}

export function deriveInvestigationProgress(
  eventTypes: string[],
  status: "open" | "investigating" | "resolved" | "failed",
): InvestigationProgress {
  const completed = new Set<number>();
  let currentIndex: number | null = status === "investigating" ? 0 : null;

  for (const eventType of eventTypes) {
    switch (eventType) {
      case "investigation_started":
        currentIndex = 0;
        break;
      case "context_collection_started":
        completed.add(0);
        currentIndex = 1;
        break;
      case "deployment_found":
        completed.add(1);
        currentIndex = 2;
        break;
      case "runtime_analysis_completed":
        completed.add(2);
        currentIndex = 3;
        break;
      case "retrieval_started":
        currentIndex = 3;
        break;
      case "documents_retrieved":
        completed.add(3);
        currentIndex = 4;
        break;
      case "hypothesis_generated":
        completed.add(4);
        currentIndex = 5;
        break;
      case "verification_started":
        currentIndex = 5;
        break;
      case "verification_completed":
        completed.add(5);
        break;
      case "investigation_refined":
        currentIndex = 3;
        break;
      case "report_generated":
        completed.add(6);
        currentIndex = 6;
        break;
      case "investigation_completed":
        workflowStages.forEach((_, index) => completed.add(index));
        currentIndex = null;
        break;
    }
  }

  if (status === "resolved") {
    workflowStages.forEach((_, index) => completed.add(index));
    currentIndex = null;
  }

  const completedSteps = workflowStages.map((_, index) => completed.has(index));
  const showPercentage = status !== "open" && (eventTypes.length > 0 || status === "resolved");
  return {
    completedSteps,
    currentIndex,
    failedIndex: status === "failed" ? (currentIndex ?? 0) : null,
    percentage: showPercentage
      ? Math.round((completed.size / workflowStages.length) * 100)
      : null,
  };
}
