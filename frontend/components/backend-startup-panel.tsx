import Link from "next/link";
import { ArrowRight, RotateCw } from "lucide-react";
import type { BackendRuntimeStatus } from "../lib/backend-runtime";
import { ActivityRail } from "./activity-rail";

interface BackendStartupPanelProps {
  status: BackendRuntimeStatus;
  isLocal: boolean;
}

/** The fallback is intentionally user-triggered; automatic runtime polling remains primary. */
export function refreshPage(reload: () => void = () => window.location.reload()): void {
  reload();
}

export function BackendStartupPanel({ status, isLocal }: BackendStartupPanelProps) {
  const ready = status === "ready";
  const longWait = status === "long_wait";
  const title = ready
    ? "Investigation runtime ready"
    : longWait
      ? "Taking longer than expected"
      : status === "checking"
        ? "Connecting to the investigation runtime"
        : isLocal
          ? "TraceLens backend is unavailable"
          : "TraceLens backend is waking up";

  const body = ready
    ? "Backend connected. Live incident data and investigations are available."
    : longWait
      ? isLocal
        ? "The local backend is still unavailable."
        : "The hosted backend is still starting. TraceLens will keep trying automatically."
    : status === "checking"
      ? "TraceLens is checking the configured backend health endpoint before loading live incident data."
    : isLocal
      ? "The local API is not responding. TraceLens will reconnect automatically when the backend is available."
      : "The public demo uses a free hosted backend that may spin down after inactivity. TraceLens will reconnect automatically when the investigation runtime is ready.";

  return (
    <section
      className={`backend-startup ${ready ? "ready" : longWait ? "long-wait" : "running"}`}
      aria-live="polite"
    >
      <div className="backend-startup-copy">
        <div>
          <div className="eyebrow">Demo runtime</div>
          <h1>{title}</h1>
          <p>{body}</p>
          {!ready && !isLocal && !longWait && (
            <p className="backend-startup-secondary">Usually ready within 1–2 minutes.</p>
          )}
          {longWait && (
            <p className="backend-startup-secondary">
              If the page appears stuck, you can refresh and reconnect.
            </p>
          )}
        </div>
        {longWait ? (
          <button className="button small" type="button" onClick={() => refreshPage()}>
            <RotateCw size={14} aria-hidden="true" /> Refresh page
          </button>
        ) : !ready ? (
          <Link className="button small" href="/about">
            Read System Briefing <ArrowRight size={13} />
          </Link>
        ) : null}
      </div>
      <div className="backend-startup-status">
        <span>
          {ready
            ? "Ready"
            : longWait
              ? "Connection unavailable"
              : status === "checking"
                ? "Checking backend health…"
                : "Initializing investigation runtime…"}
        </span>
        {!ready && !longWait && (
          <small>While you wait, explore how TraceLens investigates an incident below.</small>
        )}
      </div>
      <ActivityRail state={ready ? "completed" : longWait ? "failed" : "running"} />
    </section>
  );
}
