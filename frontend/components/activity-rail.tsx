export type ActivityRailState = "idle" | "running" | "completed" | "failed";

export function ActivityRail({ state }: { state: ActivityRailState }) {
  return <div className={`activity-rail ${state}`} aria-hidden="true" />;
}
