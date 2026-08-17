import { API_BASE } from "./api";

export type BackendRuntimeStatus = "checking" | "waking" | "ready" | "long_wait";

export interface BackendRuntimeSnapshot {
  status: BackendRuntimeStatus;
}

export const BACKEND_POLL_INTERVAL_MS = 5_000;
export const BACKEND_LONG_WAIT_MS = 120_000;

export function isLocalApiBase(apiBase = API_BASE): boolean {
  try {
    const hostname = new URL(apiBase).hostname;
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
  } catch {
    return false;
  }
}

export async function probeBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok) return false;
    const body = (await response.json()) as { status?: string };
    return body.status === "healthy";
  } catch {
    return false;
  }
}

type Schedule = (callback: () => void, delay: number) => ReturnType<typeof setTimeout>;
type Cancel = (timer: ReturnType<typeof setTimeout>) => void;

export class BackendRuntimeMonitor {
  private snapshot: BackendRuntimeSnapshot = { status: "checking" };
  private listeners = new Set<(snapshot: BackendRuntimeSnapshot) => void>();
  private timer: ReturnType<typeof setTimeout> | null = null;
  private startedAt = 0;
  private generation = 0;
  private stopped = true;

  constructor(
    private readonly probe: () => Promise<boolean> = probeBackendHealth,
    private readonly pollIntervalMs = BACKEND_POLL_INTERVAL_MS,
    private readonly longWaitMs = BACKEND_LONG_WAIT_MS,
    private readonly now: () => number = Date.now,
    private readonly schedule: Schedule = setTimeout,
    private readonly cancel: Cancel = clearTimeout,
  ) {}

  getSnapshot = (): BackendRuntimeSnapshot => this.snapshot;

  subscribe = (listener: (snapshot: BackendRuntimeSnapshot) => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  start(): void {
    this.beginProbeCycle();
  }

  retry(): void {
    this.beginProbeCycle();
  }

  stop(): void {
    this.stopped = true;
    this.generation += 1;
    this.clearTimer();
  }

  private beginProbeCycle(): void {
    this.stopped = false;
    this.generation += 1;
    this.clearTimer();
    this.startedAt = this.now();
    this.setSnapshot({ status: "checking" });
    void this.runProbe(this.generation);
  }

  private async runProbe(generation: number): Promise<void> {
    const healthy = await this.probe();
    if (this.stopped || generation !== this.generation) return;

    if (healthy) {
      this.clearTimer();
      this.setSnapshot({ status: "ready" });
      return;
    }

    const elapsed = this.now() - this.startedAt;
    this.setSnapshot({ status: elapsed >= this.longWaitMs ? "long_wait" : "waking" });
    this.timer = this.schedule(() => void this.runProbe(generation), this.pollIntervalMs);
  }

  private clearTimer(): void {
    if (this.timer === null) return;
    this.cancel(this.timer);
    this.timer = null;
  }

  private setSnapshot(snapshot: BackendRuntimeSnapshot): void {
    this.snapshot = snapshot;
    this.listeners.forEach((listener) => listener(snapshot));
  }
}

export function shouldShowRuntimeBriefing(
  status: BackendRuntimeStatus,
  pathname: string,
): boolean {
  return pathname !== "/about" && status !== "ready";
}
