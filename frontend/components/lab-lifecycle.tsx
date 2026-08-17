import { Check } from "lucide-react";
import type { LabLifecycleStage } from "@/lib/lab-workflow";

export function LabLifecycle({ stages }: { stages: LabLifecycleStage[] }) {
  return (
    <div className="lab-lifecycle-scroll" aria-label="Incident Lab lifecycle">
      <ol className="lab-lifecycle">
        {stages.map((stage, index) => (
          <li className={stage.state} key={index}>
            <span className="lab-lifecycle-node">
              {stage.state === "completed" ? <Check size={12} /> : index + 1}
            </span>
            <span>{stage.label}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
