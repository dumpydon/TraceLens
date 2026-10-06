import { afterEach, describe, expect, it, vi } from "vitest";
import { activateWarmWindow } from "./warm-window";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

describe("optional warm activation", () => {
  it("posts to the public Worker during hosted production bootstrap", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_WARM_CONTROL_URL", "https://warm.test");
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ active: true }));
    await activateWarmWindow(false);
    expect(fetch).toHaveBeenCalledWith(new URL("https://warm.test/api/warm/activate"),
      expect.objectContaining({ method: "POST", keepalive: true, cache: "no-store" }));
    expect(fetch.mock.calls[0][1]?.headers).toBeUndefined();
  });

  it("silently tolerates network, HTTP and invalid configuration failures", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_WARM_CONTROL_URL", "https://warm.test");
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("unavailable"));
    await expect(activateWarmWindow(false)).resolves.toBeUndefined();
    fetch.mockResolvedValue(new Response(null, { status: 503 }));
    await expect(activateWarmWindow(false)).resolves.toBeUndefined();
    vi.stubEnv("NEXT_PUBLIC_WARM_CONTROL_URL", "invalid");
    await expect(activateWarmWindow(false)).resolves.toBeUndefined();
  });

  it("does not activate for localhost, development, or missing configuration", async () => {
    const fetch = vi.spyOn(globalThis, "fetch");
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_WARM_CONTROL_URL", "https://warm.test");
    await activateWarmWindow(true);
    vi.stubEnv("NODE_ENV", "development");
    await activateWarmWindow(false);
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_WARM_CONTROL_URL", "");
    await activateWarmWindow(false);
    expect(fetch).not.toHaveBeenCalled();
  });
});
