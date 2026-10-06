import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import worker, {
  activateLease, DAILY_CRON, dailyExpiry, handleActivation, handleScheduled,
  KEEPALIVE_CRON, WARM_KEY, WARM_WINDOW_MS, type WarmEnv,
} from "../src/index";

function fixture(expiry?: number) {
  const values = new Map<string, string>();
  if (expiry !== undefined) values.set(WARM_KEY, String(expiry));
  const env: WarmEnv = {
    TRACELENS_STATE: {
      get: vi.fn(async (key: string) => values.get(key) ?? null),
      put: vi.fn(async (key: string, value: string) => { values.set(key, value); }),
    },
    RENDER_API_BASE_URL: "https://tracelens-uh8e.onrender.com",
    FRONTEND_ORIGIN: "https://tracelens-seven.vercel.app",
    TRACELENS_KEEPALIVE_SECRET: "test-maintenance-token",
  };
  return { env, values };
}

const time = (value: string) => Date.parse(`2026-10-06T${value}:00Z`);
const response = (body: object, status = 200) => Response.json(body, { status });

beforeEach(() => {
  vi.spyOn(console, "info").mockImplementation(() => undefined);
  vi.spyOn(console, "warn").mockImplementation(() => undefined);
});
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

describe("global fixed lease", () => {
  it("creates exactly three hours at 10:00", async () => {
    const { env, values } = fixture();
    expect(await activateLease(env, time("10:00"))).toEqual({
      active: true, created: true, warm_until: new Date(time("13:00")).toISOString(),
    });
    expect(values.get(WARM_KEY)).toBe(String(time("13:00")));
  });

  it.each(["11:00", "12:59"])("does not extend the 13:00 lease at %s", async (visit) => {
    const { env } = fixture(time("13:00"));
    expect(await activateLease(env, time(visit))).toMatchObject({
      created: false, warm_until: new Date(time("13:00")).toISOString(),
    });
    expect(env.TRACELENS_STATE.put).not.toHaveBeenCalled();
  });

  it("creates a new three-hour window after expiry and at the exact boundary", async () => {
    const { env } = fixture(time("13:00"));
    expect(await activateLease(env, time("13:01"))).toMatchObject({
      created: true, warm_until: new Date(time("16:01")).toISOString(),
    });
    const boundary = fixture(time("13:00"));
    expect((await activateLease(boundary.env, time("13:00"))).created).toBe(true);
  });

  it.each(["garbage", "Infinity", "-1", "9999999999999999", ""])("replaces malformed expiry %s", async (raw) => {
    const { env, values } = fixture();
    values.set(WARM_KEY, raw);
    await activateLease(env, time("10:00"));
    expect(values.get(WARM_KEY)).toBe(String(time("13:00")));
  });

  it("makes one lightweight health call during the lease", async () => {
    const { env } = fixture(time("13:00"));
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ status: "healthy" }));
    await handleScheduled({ cron: KEEPALIVE_CRON, scheduledTime: time("12:50") }, env, time("12:50"));
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith(new URL(`${env.RENDER_API_BASE_URL}/health`), expect.objectContaining({ method: "GET" }));
    expect(console.info).toHaveBeenCalledWith("warm.render_succeeded", { status: 200 });
  });

  it.each(["13:00", "13:10"])("skips keepalive at/after expiry: %s", async (now) => {
    const { env } = fixture(time("13:00"));
    const fetch = vi.spyOn(globalThis, "fetch");
    await handleScheduled({ cron: KEEPALIVE_CRON, scheduledTime: time(now) }, env, time(now));
    expect(fetch).not.toHaveBeenCalled();
  });
});

describe("daily morning window", () => {
  it("anchors noon IST and contacts the protected PostgreSQL endpoint immediately", async () => {
    const { env, values } = fixture();
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(response({
      status: "ok", database: "postgresql", checked_at: new Date(time("03:30")).toISOString(),
    }));
    expect(dailyExpiry(time("03:30"))).toBe(time("06:30"));
    await handleScheduled({ cron: DAILY_CRON, scheduledTime: time("03:30") }, env, time("03:30"));
    expect(values.get(WARM_KEY)).toBe(String(time("06:30")));
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith(new URL(`${env.RENDER_API_BASE_URL}/internal/maintenance/heartbeat`),
      expect.objectContaining({ method: "POST", headers: { Authorization: `Bearer ${env.TRACELENS_KEEPALIVE_SECRET}` } }));
  });

  it.each([["05:30", "06:30"], ["06:00", "06:30"], ["07:30", "07:30"]])(
    "extends shorter leases but preserves longer ones: %s", async (existing, expected) => {
      const { env, values } = fixture(time(existing));
      vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ status: "ok", database: "postgresql", checked_at: "now" }));
      await handleScheduled({ cron: DAILY_CRON, scheduledTime: time("03:30") }, env, time("03:30"));
      expect(values.get(WARM_KEY)).toBe(String(time(expected)));
    },
  );

  it("does not slide the noon IST daily lease on a 10:30 IST browser revisit", async () => {
    const { env } = fixture(time("06:30"));
    expect((await activateLease(env, time("05:00"))).warm_until).toBe(new Date(time("06:30")).toISOString());
    expect(env.TRACELENS_STATE.put).not.toHaveBeenCalled();
  });

  it("is idempotent and the ten-minute event skips the daily boundary", async () => {
    const { env, values } = fixture();
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response({ status: "ok", database: "postgresql", checked_at: "now" }));
    const event = { cron: DAILY_CRON, scheduledTime: time("03:30") };
    await handleScheduled(event, env, time("03:30"));
    await handleScheduled(event, env, time("03:31"));
    await handleScheduled({ ...event, cron: KEEPALIVE_CRON }, env, time("03:30"));
    expect(values.get(WARM_KEY)).toBe(String(time("06:30")));
    expect(env.TRACELENS_STATE.put).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("does not revive a late daily event beyond its anchored window", async () => {
    const { env } = fixture();
    const fetch = vi.spyOn(globalThis, "fetch");
    await handleScheduled({ cron: DAILY_CRON, scheduledTime: time("03:30") }, env, time("06:31"));
    expect(fetch).not.toHaveBeenCalled();
    expect(env.TRACELENS_STATE.put).not.toHaveBeenCalled();
  });

  it("handles DB failure with bounded retries and keeps the lease intact", async () => {
    vi.useFakeTimers();
    const { env, values } = fixture();
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response({ detail: "Database unavailable" }, 503));
    const pending = handleScheduled({ cron: DAILY_CRON, scheduledTime: time("03:30") }, env, time("03:30"));
    await vi.advanceTimersByTimeAsync(20_000);
    await pending;
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(values.get(WARM_KEY)).toBe(String(time("06:30")));
    expect(console.warn).toHaveBeenCalledWith("warm.database_heartbeat_failed");
  });

  it("rejects cached/incomplete database status as heartbeat proof", async () => {
    const { env } = fixture();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ status: "ok", database: "connected" }));
    await handleScheduled({ cron: DAILY_CRON, scheduledTime: time("03:30") }, env, time("03:30"));
    expect(console.warn).toHaveBeenCalledWith("warm.database_heartbeat_invalid_response");
  });
});

describe("failure isolation and activation surface", () => {
  it("fails activation safely on KV failure; daily still attempts the DB heartbeat", async () => {
    const { env } = fixture();
    vi.mocked(env.TRACELENS_STATE.get).mockRejectedValue(new Error("credential must not be logged"));
    const activation = await handleActivation(new Request("https://worker.test/api/warm/activate", { method: "POST" }), env);
    expect(activation.status).toBe(503);
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ status: "ok", database: "postgresql", checked_at: "now" }));
    await handleScheduled({ cron: KEEPALIVE_CRON, scheduledTime: time("04:00") }, env, time("04:00"));
    expect(fetch).not.toHaveBeenCalled();
    await handleScheduled({ cron: DAILY_CRON, scheduledTime: time("03:30") }, env, time("03:30"));
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(vi.mocked(console.warn).mock.calls)).not.toContain("credential");
  });

  it("handles Render failure without rewriting a valid lease", async () => {
    const { env, values } = fixture(time("13:00"));
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("secret in network error"));
    await handleScheduled({ cron: KEEPALIVE_CRON, scheduledTime: time("12:50") }, env, time("12:50"));
    expect(values.get(WARM_KEY)).toBe(String(time("13:00")));
    expect(env.TRACELENS_STATE.put).not.toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalledWith("warm.render_failed");
  });

  it("allows only the production browser origin, POST and preflight, without a client expiry", async () => {
    vi.useFakeTimers(); vi.setSystemTime(time("10:00"));
    const { env } = fixture();
    const request = (method: string, origin = env.FRONTEND_ORIGIN) => new Request("https://worker.test/api/warm/activate", {
      method, headers: { Origin: origin }, ...(method === "POST" ? { body: JSON.stringify({ warm_until: "2099-01-01" }) } : {}),
    });
    expect((await handleActivation(request("OPTIONS"), env)).status).toBe(204);
    expect((await handleActivation(request("GET"), env)).status).toBe(405);
    expect((await handleActivation(request("POST", "https://attacker.test"), env)).status).toBe(403);
    const result = await handleActivation(request("POST"), env);
    expect(result.headers.get("Access-Control-Allow-Origin")).toBe(env.FRONTEND_ORIGIN);
    expect((await result.json()).warm_until).toBe(new Date(time("13:00")).toISOString());
    expect((await handleActivation(new Request("https://worker.test/health"), env)).status).toBe(404);
  });

  it("registers the scheduled promise with the Worker context", async () => {
    const { env } = fixture();
    const promises: Promise<void>[] = [];
    worker.scheduled({ cron: KEEPALIVE_CRON, scheduledTime: time("04:00") }, env, { waitUntil: p => { promises.push(p); } });
    expect(promises).toHaveLength(1);
    await promises[0];
  });
});
