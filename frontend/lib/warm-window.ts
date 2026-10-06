/** Best effort only: runtime polling and navigation never wait for this call. */
export async function activateWarmWindow(isLocal: boolean): Promise<void> {
  const base = process.env.NEXT_PUBLIC_WARM_CONTROL_URL;
  if (process.env.NODE_ENV !== "production" || isLocal || !base) return;

  try {
    const url = new URL("/api/warm/activate", base);
    if (url.protocol !== "https:") return;
    await fetch(url, {
      method: "POST",
      cache: "no-store",
      keepalive: true,
      signal: AbortSignal.timeout(5_000),
    });
  } catch {
    // The existing backend wake/recovery experience remains authoritative.
  }
}
