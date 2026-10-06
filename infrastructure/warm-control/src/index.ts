export const WARM_KEY = "render_warm_until";
export const WARM_WINDOW_MS = 3 * 60 * 60 * 1_000;
export const KEEPALIVE_CRON = "*/10 * * * *";
export const DAILY_CRON = "30 3 * * *";

export interface WarmEnv {
  TRACELENS_STATE: {
    get(key: string): Promise<string | null>;
    put(key: string, value: string): Promise<void>;
  };
  RENDER_API_BASE_URL: string;
  FRONTEND_ORIGIN: string;
  TRACELENS_KEEPALIVE_SECRET?: string;
}

export interface WarmEvent {
  cron: string;
  scheduledTime: number;
}

async function readExpiry(env: WarmEnv): Promise<number> {
  const raw = await env.TRACELENS_STATE.get(WARM_KEY);
  if (!raw || !/^\d+$/.test(raw)) return 0;
  const expiry = Number(raw);
  return Number.isSafeInteger(expiry) && expiry > 0 && expiry <= 8_640_000_000_000_000 ? expiry : 0;
}

export async function activateLease(env: WarmEnv, now = Date.now()) {
  const existing = await readExpiry(env);
  const created = existing <= now;
  const expiry = created ? now + WARM_WINDOW_MS : existing;
  if (created) await env.TRACELENS_STATE.put(WARM_KEY, String(expiry));
  console.info(created ? "warm.user_lease_created" : "warm.active_lease_reused", { warm_until: expiry });
  return { active: true, created, warm_until: new Date(expiry).toISOString() };
}

// Noon IST = 06:30 UTC, anchored to the scheduled date rather than invocation time.
export function dailyExpiry(scheduledTime: number): number {
  const ist = new Date(scheduledTime + 330 * 60_000);
  return Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate(), 6, 30);
}

async function ensureDailyLease(env: WarmEnv, expiry: number): Promise<void> {
  const existing = await readExpiry(env);
  const effective = Math.max(existing, expiry);
  if (effective !== existing) await env.TRACELENS_STATE.put(WARM_KEY, String(effective));
  console.info("warm.daily_window_ensured", { warm_until: effective });
}

function backendUrl(env: WarmEnv, path: string): URL {
  const base = new URL(env.RENDER_API_BASE_URL);
  if (base.protocol !== "https:") throw new Error("Invalid backend configuration");
  return new URL(path, base.origin);
}

async function pingHealth(env: WarmEnv): Promise<void> {
  try {
    const response = await fetch(backendUrl(env, "/health"), {
      method: "GET", redirect: "manual", cache: "no-store", signal: AbortSignal.timeout(15_000),
    });
    const body = response.ok ? await response.json() as { status?: string } : null;
    if (!response.ok) await response.body?.cancel();
    console.info(response.ok && body?.status === "healthy" ? "warm.render_succeeded" : "warm.render_failed", {
      status: response.status,
    });
  } catch {
    console.warn("warm.render_failed");
  }
}

async function pauseBeforeRetry(signal: AbortSignal): Promise<void> {
  if (signal.aborted) return;
  await new Promise<void>((resolve) => {
    const finish = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", finish);
      resolve();
    };
    const timer = setTimeout(finish, 10_000);
    signal.addEventListener("abort", finish, { once: true });
  });
}

async function dailyHeartbeat(env: WarmEnv): Promise<void> {
  if (!env.TRACELENS_KEEPALIVE_SECRET) {
    console.warn("warm.database_heartbeat_unconfigured");
    await pingHealth(env);
    return;
  }
  // The first POST also wakes Render. Bounded retries allow an early cold-start 503.
  const signal = AbortSignal.timeout(90_000);
  try {
    const url = backendUrl(env, "/internal/maintenance/heartbeat");
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const response = await fetch(url, {
          method: "POST", redirect: "manual", cache: "no-store", signal,
          headers: { Authorization: `Bearer ${env.TRACELENS_KEEPALIVE_SECRET}` },
        });
        if (response.ok) {
          const result = await response.json() as { status?: string; database?: string; checked_at?: string };
          if (result.status === "ok" && result.database === "postgresql" && result.checked_at) {
            console.info("warm.database_heartbeat_succeeded", { checked_at: result.checked_at });
            return;
          }
          console.warn("warm.database_heartbeat_invalid_response");
          return;
        }
        await response.body?.cancel();
        if (response.status < 500 && response.status !== 429) break;
      } catch {
        if (signal.aborted) break;
      }
      if (attempt < 2) await pauseBeforeRetry(signal);
      if (signal.aborted) break;
    }
  } catch {
    // Never log driver/request errors or headers: they can contain credentials.
  }
  console.warn("warm.database_heartbeat_failed");
}

export async function handleScheduled(event: WarmEvent, env: WarmEnv, now = Date.now()): Promise<void> {
  if (event.cron === DAILY_CRON) {
    const expiry = dailyExpiry(event.scheduledTime);
    if (now >= expiry) {
      console.info("warm.daily_window_expired");
      return;
    }
    try {
      await ensureDailyLease(env, expiry);
    } catch {
      console.warn("warm.daily_storage_failed");
    }
    // Even a KV failure must not prevent the immediate morning wake/database attempt.
    await dailyHeartbeat(env);
    return;
  }
  if (event.cron !== KEEPALIVE_CRON) return;
  const scheduled = new Date(event.scheduledTime);
  // The daily trigger owns this boundary; avoid duplicate requests without locking.
  if (scheduled.getUTCHours() === 3 && scheduled.getUTCMinutes() === 30) return;
  try {
    if (await readExpiry(env) <= now) {
      console.info("warm.keepalive_skipped");
      return;
    }
    await pingHealth(env);
  } catch {
    console.warn("warm.keepalive_storage_failed");
  }
}

export async function handleActivation(request: Request, env: WarmEnv): Promise<Response> {
  const headers = new Headers({ "Cache-Control": "no-store", Vary: "Origin" });
  if (new URL(request.url).pathname !== "/api/warm/activate") {
    return new Response("Not found", { status: 404, headers });
  }
  const origin = request.headers.get("Origin");
  if (origin && origin !== env.FRONTEND_ORIGIN) {
    return new Response("Origin not allowed", { status: 403, headers });
  }
  if (origin) headers.set("Access-Control-Allow-Origin", origin);
  if (request.method === "OPTIONS") {
    headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
    headers.set("Access-Control-Allow-Headers", "Content-Type");
    return new Response(null, { status: 204, headers });
  }
  if (request.method !== "POST") {
    headers.set("Allow", "POST, OPTIONS");
    return new Response("Method not allowed", { status: 405, headers });
  }
  try {
    // Ignore any request body; expiry and duration are exclusively server controlled.
    return Response.json(await activateLease(env), { headers });
  } catch {
    console.warn("warm.activation_unavailable");
    return Response.json({ active: false }, { status: 503, headers });
  }
}

export default {
  fetch: handleActivation,
  scheduled(event: WarmEvent, env: WarmEnv, context: { waitUntil(promise: Promise<void>): void }) {
    context.waitUntil(handleScheduled(event, env));
  },
};
