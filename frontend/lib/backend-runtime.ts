import { API_BASE } from "./api";

export type BackendRuntimeStatus = "checking" | "waking" | "ready" | "long_wait";

export interface BackendRuntimeSnapshot {
  status: BackendRuntimeStatus;
}

export const BACKEND_POLL_INTERVAL_MS = 5_000;
export const BACKEND_LONG_WAIT_MS = 120_000;
export const BACKEND_HEALTH_TIMEOUT_MS = 8_000;

export function isLocalApiBase(apiBase = API_BASE): boolean {
  try {
    const hostname = new URL(apiBase).hostname;
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
  } catch {
    return false;
  }
}

export async function probeBackendHealth(parentSignal?: AbortSignal): Promise<boolean> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), BACKEND_HEALTH_TIMEOUT_MS);
  const abortFromParent = () => controller.abort();
  if (parentSignal?.aborted) controller.abort();
  parentSignal?.addEventListener("abort", abortFromParent, { once: true });

  try {
    const response = await fetch(`${API_BASE}/health`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) return false;
    const body = (await response.json()) as { status?: string };
    return body.status === "healthy";
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
    parentSignal?.removeEventListener("abort", abortFromParent);
  }
}

type Schedule = (callback: () => void, delay: number) => ReturnType<typeof setTimeout>;
type Cancel = (timer: ReturnType<typeof setTimeout>) => void;
type Probe = (signal: AbortSignal) => Promise<boolean>;

export class BackendRuntimeMonitor {
  private snapshot: BackendRuntimeSnapshot = { status: "checking" };
  private listeners = new Set<(snapshot: BackendRuntimeSnapshot) => void>();
  private timer: ReturnType<typeof setTimeout> | null = null;
  private waitingResolve: ((continuePolling: boolean) => void) | null = null;
  private activeController: AbortController | null = null;
  private startedAt = 0;
  private generation = 0;
  private stopped = true;
  private active = false;
  private retryRequested = false;

  constructor(
    private readonly probe: Probe = probeBackendHealth,
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
    if (this.active) return;
    this.beginProbeCycle();
  }

  retry(): void {
    if (!this.active) {
      this.beginProbeCycle();
      return;
    }

    this.startedAt = this.now();
    this.setSnapshot({ status: "checking" });
    if (this.waitingResolve) {
      const resolveWait = this.waitingResolve;
      this.retryRequested = false;
      resolveWait(true);
      return;
    }
    this.retryRequested = true;
  }

  stop(): void {
    this.stopped = true;
    this.generation += 1;
    this.active = false;
    this.retryRequested = false;
    this.activeController?.abort();
    this.activeController = null;
    this.resolveWait(false);
  }

  private beginProbeCycle(): void {
    this.stopped = false;
    this.generation += 1;
    this.active = true;
    this.retryRequested = false;
    this.startedAt = this.now();
    this.setSnapshot({ status: "checking" });
    void this.runLoop(this.generation);
  }

  private async runLoop(generation: number): Promise<void> {
    try {
      while (!this.stopped && generation === this.generation) {
        const healthy = await this.runProbe();
        if (this.stopped || generation !== this.generation) return;

        if (healthy) {
          this.setSnapshot({ status: "ready" });
          return;
        }

        const elapsed = this.now() - this.startedAt;
        this.setSnapshot({ status: elapsed >= this.longWaitMs ? "long_wait" : "waking" });

        const retryNow = this.retryRequested;
        this.retryRequested = false;
        if (!retryNow && !(await this.waitForNextProbe(generation))) return;
      }
    } finally {
      if (generation === this.generation) this.active = false;
    }
  }

  private async runProbe(): Promise<boolean> {
    const controller = new AbortController();
    this.activeController = controller;
    try {
      return await this.probe(controller.signal);
    } catch {
      return false;
    } finally {
      if (this.activeController === controller) this.activeController = null;
    }
  }

  private waitForNextProbe(generation: number): Promise<boolean> {
    if (this.stopped || generation !== this.generation) return Promise.resolve(false);

    return new Promise((resolve) => {
      const finish = (continuePolling: boolean) => {
        if (this.waitingResolve !== finish) return;
        this.waitingResolve = null;
        if (this.timer !== null) {
          this.cancel(this.timer);
          this.timer = null;
        }
        resolve(continuePolling);
      };

      this.waitingResolve = finish;
      this.timer = this.schedule(() => finish(true), this.pollIntervalMs);
    });
  }

  private resolveWait(continuePolling: boolean): void {
    const resolveWait = this.waitingResolve;
    if (resolveWait) resolveWait(continuePolling);
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
