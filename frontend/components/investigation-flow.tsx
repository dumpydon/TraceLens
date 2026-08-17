import { deriveInvestigationProgress, workflowStages } from "@/lib/format";
import type { IncidentStatus, InvestigationEvent } from "@/lib/types";
import { ActivityRail, type ActivityRailState } from "@/components/activity-rail";

export function InvestigationFlow({ events, status, refinements = 0 }: { events: InvestigationEvent[]; status: IncidentStatus; refinements?: number }) {
  const progress = deriveInvestigationProgress(events.map((event) => event.event_type), status);
  const railState: ActivityRailState = status === "investigating" ? "running" : status === "resolved" ? "completed" : status === "failed" ? "failed" : "idle";
  return <div className={`investigation-progress ${status}`}>
    {(progress.percentage !== null || refinements > 0) && <div className="flow-meta">
      {refinements > 0 && <span className="refine-note">↺ refined {refinements}×</span>}
      {progress.percentage !== null && <span className="flow-percent">{progress.percentage}%</span>}
    </div>}
    <ActivityRail state={railState} />
    <div className="flow-scroll">
      <ol className="flow" aria-label="Investigation progress">
        {workflowStages.map((item, index) => {
          const done = progress.completedSteps[index];
          const active = progress.currentIndex === index;
          const failed = progress.failedIndex === index;
          const state = failed ? "failed" : active ? "active" : done ? "done" : "upcoming";
          return <li className={`flow-step ${state} ${done ? "completed" : ""}`} key={item.key} aria-current={active ? "step" : undefined} aria-label={`${index + 1}. ${item.label} · ${state}`}>
            <span className="flow-node" aria-hidden="true">{index + 1}</span>
            <span className="flow-label">{item.label}</span>
          </li>;
        })}
      </ol>
    </div>
  </div>;
}
