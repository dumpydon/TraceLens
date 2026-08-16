import { afterEach, describe, expect, it, vi } from "vitest";
import { api, BACKEND_WAKE_MESSAGE } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("incident traffic batch handoff", () => {
  it("posts the exact generated traffic batch when creating an incident", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "INC-TEST",
        title: "Checkout reliability degradation",
        service: "checkout-service",
        severity: "high",
        status: "open",
        started_at: "2026-08-15T10:00:00Z",
        summary: "",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.createIncident("BATCH-PAYMENT-LATENCY");

    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body as string)).toEqual({
      traffic_batch_id: "BATCH-PAYMENT-LATENCY",
    });
  });

  it("keeps manual incident creation backward compatible", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "INC-MANUAL" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.createIncident();

    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body as string)).toEqual({});
  });

  it("shows a restrained wake-up error when the demo backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    await expect(api.overview()).rejects.toThrow(BACKEND_WAKE_MESSAGE);
  });

  it("uses the configured production API origin without a trailing slash", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://tracelens-api.onrender.com/");
    vi.resetModules();
    const productionApi = await import("./api");

    expect(productionApi.API_BASE).toBe("https://tracelens-api.onrender.com");
  });
});
