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

export const workflowStages = ["context", "runtime", "retrieval", "hypothesis", "verify", "report"] as const;

export function stageIndex(stage?: string): number {
  return Math.max(0, workflowStages.indexOf(stage as (typeof workflowStages)[number]));
}

