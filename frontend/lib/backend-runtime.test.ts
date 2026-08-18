import { describe, expect, it, vi } from "vitest";
import {
  BACKEND_HEALTH_TIMEOUT_MS,
  BackendRuntimeMonitor,
  isLocalApiBase,
  probeBackendHealth,
  shouldShowRuntimeBriefing,
} from "./backend-runtime";

async function settle(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

describe("BackendRuntimeMonitor", () => {
  it("polls while waking and stops scheduling after the backend becomes ready", async () => {
    const results = [false, true];
    const scheduled: Array<() => void> = [];
    const monitor = new BackendRuntimeMonitor(
      async () => results.shift() ?? true,
      5_000,
      120_000,
      () => 0,
      (callback) => {
        scheduled.push(callback);
        return scheduled.length as unknown as ReturnType<typeof setTimeout>;
      },
      () => undefined,
    );

    monitor.start();
    await settle();
    expect(monitor.getSnapshot().status).toBe("waking");
    expect(scheduled).toHaveLength(1);

    scheduled.shift()?.();
    await settle();
    expect(monitor.getSnapshot().status).toBe("ready");
    expect(scheduled).toHaveLength(0);
  });

  it("continues polling after long-wait and recovers automatically", async () => {
    let now = 0;
    let healthy = false;
    let calls = 0;
    const scheduled: Array<() => void> = [];
    const monitor = new BackendRuntimeMonitor(
      async () => {
        calls += 1;
        return healthy;
      },
      5_000,
      100,
      () => now,
      (callback) => {
        scheduled.push(callback);
        return scheduled.length as unknown as ReturnType<typeof setTimeout>;
      },
      () => undefined,
    );

    monitor.start();
    await settle();
    now = 120_000;
    scheduled.shift()?.();
    await settle();
    expect(monitor.getSnapshot().status).toBe("long_wait");
    expect(scheduled).toHaveLength(1);

    now = 125_000;
    scheduled.shift()?.();
    await settle();
    expect(calls).toBe(3);
    expect(monitor.getSnapshot().status).toBe("long_wait");
    expect(scheduled).toHaveLength(1);

    healthy = true;
    scheduled.shift()?.();
    await settle();
    expect(monitor.getSnapshot().status).toBe("ready");
    expect(calls).toBe(4);
    expect(scheduled).toHaveLength(0);
  });

  it("does not overlap health probes when retry is requested", async () => {
    let calls = 0;
    const probeControl: { release: ((healthy: boolean) => void) | null } = { release: null };
    const monitor = new BackendRuntimeMonitor(
      () => {
        calls += 1;
        return new Promise<boolean>((resolve) => { probeControl.release = resolve; });
      },
    );

    monitor.start();
    await settle();
    expect(calls).toBe(1);

    monitor.retry();
    await settle();
    expect(calls).toBe(1);

    probeControl.release?.(false);
    await settle();
    expect(calls).toBe(2);
    monitor.stop();
  });

  it("aborts a hanging health request at the timeout", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) => (
      new Promise<Response>((_, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
      })
    ));

    try {
      const pending = probeBackendHealth();
      await vi.advanceTimersByTimeAsync(BACKEND_HEALTH_TIMEOUT_MS);
      await expect(pending).resolves.toBe(false);
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/health"),
        expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
      );
    } finally {
      fetchMock.mockRestore();
      vi.useRealTimers();
    }
  });

  it("requires the expected healthy status in a successful response", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "warming" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    try {
      await expect(probeBackendHealth()).resolves.toBe(false);
    } finally {
      fetchMock.mockRestore();
    }
  });

  it("aborts an active probe and clears a pending poll on stop", async () => {
    let receivedSignal: AbortSignal | undefined;
    const scheduled: Array<() => void> = [];
    let cancelled = 0;
    const monitor = new BackendRuntimeMonitor(
      (signal) => {
        receivedSignal = signal;
        return new Promise<boolean>(() => undefined);
      },
      5_000,
      120_000,
      Date.now,
      (callback) => {
        scheduled.push(callback);
        return scheduled.length as unknown as ReturnType<typeof setTimeout>;
      },
      () => { cancelled += 1; },
    );

    monitor.start();
    await settle();
    monitor.stop();
    expect(receivedSignal?.aborted).toBe(true);
    expect(scheduled).toHaveLength(0);
    expect(cancelled).toBe(0);
  });
});

describe("backend runtime presentation rules", () => {
  it("detects local API URLs", () => {
    expect(isLocalApiBase("http://127.0.0.1:8000")).toBe(true);
    expect(isLocalApiBase("http://localhost:8000")).toBe(true);
    expect(isLocalApiBase("https://tracelens-api.onrender.com")).toBe(false);
  });

  it("substitutes the static briefing for API pages until runtime state is known", () => {
    expect(shouldShowRuntimeBriefing("checking", "/incidents")).toBe(true);
    expect(shouldShowRuntimeBriefing("waking", "/evaluations")).toBe(true);
    expect(shouldShowRuntimeBriefing("long_wait", "/lab")).toBe(true);
    expect(shouldShowRuntimeBriefing("ready", "/")).toBe(false);
    expect(shouldShowRuntimeBriefing("ready", "/incidents")).toBe(false);
    expect(shouldShowRuntimeBriefing("waking", "/about")).toBe(false);
  });
});
