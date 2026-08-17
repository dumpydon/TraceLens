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

  it("sends observable presentation copy without scenario control metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "INC-PRESENTED" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.createIncident("BATCH-PRESENTED", {
      title: "Checkout timeouts with delayed payment responses",
      summary:
        "Repeated checkout 504s observed while matching payment requests complete beyond the checkout timeout budget.",
    });

    const [, init] = fetchMock.mock.calls[0];
    const body = JSON.parse(init.body as string);
    expect(body).toEqual({
      traffic_batch_id: "BATCH-PRESENTED",
      title: "Checkout timeouts with delayed payment responses",
      summary:
        "Repeated checkout 504s observed while matching payment requests complete beyond the checkout timeout budget.",
    });
    expect(body).not.toHaveProperty("scenario");
    expect(body).not.toHaveProperty("scenario_label");
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

  it("launches evaluation only through the explicit benchmark endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "running", run_id: null, error: null }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.runEvaluation();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/evaluations/run"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});
