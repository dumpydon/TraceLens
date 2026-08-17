import { describe, expect, it } from "vitest";
import {
  BackendRuntimeMonitor,
  isLocalApiBase,
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

  it("enters long-wait and retries with a fresh probe cycle", async () => {
    let now = 0;
    let healthy = false;
    const scheduled: Array<() => void> = [];
    const monitor = new BackendRuntimeMonitor(
      async () => healthy,
      5_000,
      120_000,
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

    healthy = true;
    monitor.retry();
    expect(monitor.getSnapshot().status).toBe("checking");
    await settle();
    expect(monitor.getSnapshot().status).toBe("ready");
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
    expect(shouldShowRuntimeBriefing("ready", "/incidents")).toBe(false);
    expect(shouldShowRuntimeBriefing("waking", "/about")).toBe(false);
  });
});
