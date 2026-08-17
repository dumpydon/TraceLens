import { CircleHelp } from "lucide-react";
import { ActivityRail } from "./activity-rail";

const RUNNING_DETAIL =
  "Each benchmark case runs a complete investigation — runtime analysis, knowledge retrieval, hypothesis generation, verification, and report generation — before the results are compared with known ground truth.";

export function EvaluationRunningState() {
  return (
    <section
      className="evaluation-running"
      aria-label="Evaluation benchmark running"
    >
      <div className="evaluation-running-header">
        <div aria-live="polite" role="status">
          <strong>Running evaluation benchmark…</strong>
          <p>
            Running 5 benchmark cases through the full TraceLens investigation pipeline. This
            typically takes around 3–4 minutes.
          </p>
        </div>
        <details className="evaluation-running-detail">
          <summary title={RUNNING_DETAIL}>
            <CircleHelp size={12} aria-hidden="true" />
            What&apos;s happening?
          </summary>
          <div>
            {RUNNING_DETAIL}
            <span>5 cases × ~30–45 sec each</span>
          </div>
        </details>
      </div>
      <div className="evaluation-running-sequence" aria-hidden="true">
        <span>5 benchmark cases</span><i>→</i><span>Full investigations</span><i>→</i>
        <span>Ground-truth comparison</span><i>→</i><span>Aggregate metrics</span>
      </div>
      <ActivityRail state="running" />
    </section>
  );
}
