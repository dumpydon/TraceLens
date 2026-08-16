import { stageIndex, workflowStages } from "@/lib/format";
import type { IncidentStatus } from "@/lib/types";
import { ActivityRail, type ActivityRailState } from "@/components/activity-rail";

export function InvestigationFlow({ stage, status, refinements = 0, completed = false }: { stage?: string; status: IncidentStatus; refinements?: number; completed?: boolean }) {
  const activeIndex = completed ? workflowStages.length : stageIndex(stage);
  const railState: ActivityRailState = status === "investigating" ? "running" : status === "resolved" ? "completed" : status === "failed" ? "failed" : "idle";
  return <div className={`investigation-progress ${status}`}>
    <ActivityRail state={railState} />
    <div className="flow" aria-label={`Investigation stage: ${stage ?? "not started"}`}>
      {workflowStages.map((item, index) => <div className="flow-step" key={item}>
        <div className={`flow-node ${index < activeIndex ? "done" : ""} ${index === activeIndex ? "active" : ""}`}><i />{item}</div>
        {index < workflowStages.length - 1 && <span className="flow-line" />}
      </div>)}
      {refinements > 0 && <span className="refine-note">↺ refined {refinements}×</span>}
    </div>
  </div>;
}
