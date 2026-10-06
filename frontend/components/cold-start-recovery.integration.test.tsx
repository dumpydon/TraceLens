import { act, create } from "react-test-renderer";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "./app-shell";
import { BackendRuntimeProvider, useBackendRuntime } from "./backend-runtime-provider";

const routerReplace = vi.fn();
let currentPathname = "/";
const testGlobal = globalThis as typeof globalThis & Record<string, unknown>;

vi.mock("next/navigation", () => ({
  usePathname: () => currentPathname,
  useRouter: () => ({ replace: routerReplace, push: vi.fn(), back: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={typeof href === "string" ? href : "#"} {...props}>{children}</a>
  ),
}));

vi.mock("../lib/backend-runtime", async () => {
  const actual = await vi.importActual<typeof import("../lib/backend-runtime")>("../lib/backend-runtime");
  return { ...actual, isLocalApiBase: () => false };
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
  routerReplace.mockReset();
  currentPathname = "/";
  Reflect.deleteProperty(testGlobal, "window");
  Reflect.deleteProperty(testGlobal, "IS_REACT_ACT_ENVIRONMENT");
});

describe("cold-start recovery routing", () => {
  it("redirects a hosted root from waking through ready notice completion exactly once", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_WARM_CONTROL_URL", "https://warm.test");
    vi.useFakeTimers();
    Object.defineProperty(testGlobal, "window", { configurable: true, value: testGlobal });
    testGlobal.IS_REACT_ACT_ENVIRONMENT = true;
    const browserTimer = globalThis.setTimeout;
    const browserClearTimer = globalThis.clearTimeout;
    vi.stubGlobal("setTimeout", function(this: unknown, ...args: Parameters<typeof setTimeout>) {
      if (this !== undefined && this !== globalThis) throw new TypeError("Illegal invocation");
      return browserTimer(...args);
    });
    vi.stubGlobal("clearTimeout", function(this: unknown, ...args: Parameters<typeof clearTimeout>) {
      if (this !== undefined && this !== globalThis) throw new TypeError("Illegal invocation");
      return browserClearTimer(...args);
    });
    let healthCalls = 0;
    const lifecycle: Array<{ status: string; showReadyNotice: boolean }> = [];
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input) === "https://warm.test/api/warm/activate") {
        throw new Error("Optional Worker unavailable");
      }
      if (String(input).endsWith("/health")) {
        healthCalls += 1;
        return new Response(JSON.stringify({ status: healthCalls === 1 ? "warming" : "healthy" }), {
          status: healthCalls === 1 ? 503 : 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    function LifecycleProbe() {
      const runtime = useBackendRuntime();
      lifecycle.push({ status: runtime.status, showReadyNotice: runtime.showReadyNotice });
      return null;
    }

    let renderer: ReturnType<typeof create> | undefined;
    try {
      await act(async () => {
        renderer = create(
          <BackendRuntimeProvider>
            <>
              <LifecycleProbe />
              <AppShell>{null}</AppShell>
            </>
          </BackendRuntimeProvider>,
        );
        await Promise.resolve();
      });

      expect(healthCalls).toBe(1);
      expect(fetchMock).toHaveBeenCalledWith(new URL("https://warm.test/api/warm/activate"),
        expect.objectContaining({ method: "POST" }));
      expect(lifecycle.some(({ status }) => status === "waking")).toBe(true);
      expect(routerReplace).not.toHaveBeenCalled();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5_000);
      });
      expect(healthCalls).toBe(2);
      expect(lifecycle.at(-1)).toEqual({ status: "ready", showReadyNotice: true });
      expect(routerReplace).not.toHaveBeenCalled();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1_500);
      });
      expect(routerReplace).toHaveBeenCalledTimes(1);
      expect(routerReplace).toHaveBeenCalledWith("/lab");
      expect(lifecycle.at(-1)).toEqual({ status: "ready", showReadyNotice: false });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1_500);
      });
      expect(routerReplace).toHaveBeenCalledTimes(1);
    } finally {
      if (renderer) {
        await act(async () => {
          renderer?.unmount();
        });
      }
      fetchMock.mockRestore();
    }
  });
});
