"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, CheckCircle2, RotateCcw, Send } from "lucide-react";
import { api, type TrafficGenerationResult } from "@/lib/api";
import { incidentPresentationForScenario } from "@/lib/incident-presentation";
import { deriveLabLifecycle, failedTrafficRequests } from "@/lib/lab-workflow";
import type { Incident, Scenario, ServiceHealth } from "@/lib/types";
import { ActivityRail } from "@/components/activity-rail";
import { LabLifecycle } from "@/components/lab-lifecycle";
import { StatusBadge } from "@/components/status-badge";
import { TraceWavefield } from "@/components/visuals/trace-wavefield";

function displayName(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function batchCreatedAt(endedAt: string): string {
  const ageSeconds = Math.max(0, (Date.now() - new Date(endedAt).getTime()) / 1000);
  if (ageSeconds < 60) return "just now";
  const minutes = Math.floor(ageSeconds / 60);
  return minutes < 60 ? `${minutes}m ago` : `${Math.floor(minutes / 60)}h ago`;
}

export default function LabPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [health, setHealth] = useState<ServiceHealth[]>([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [trafficBatch, setTrafficBatch] = useState<TrafficGenerationResult | null>(null);
  const [trafficScenarioName, setTrafficScenarioName] = useState<string | null>(null);
  const [createdIncident, setCreatedIncident] = useState<Incident | null>(null);

  const load = useCallback(
    () =>
      Promise.all([api.scenarios().then(setScenarios), api.labHealth().then(setHealth)])
        .then(() => setError(""))
        .catch((err) => setError(err.message)),
    [],
  );

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  const activeExperiment = useMemo(
    () => scenarios.find((scenario) => scenario.active && scenario.name !== "baseline") ?? null,
    [scenarios],
  );
  const lifecycle = deriveLabLifecycle({
    scenarioActive: Boolean(activeExperiment),
    trafficGenerated: Boolean(trafficBatch),
    investigationCreated: Boolean(createdIncident),
  });

  async function activate(name: string) {
    setBusy(name);
    setError("");
    setMessage("");
    try {
      await api.activateScenario(name);
      setTrafficBatch(null);
      setTrafficScenarioName(null);
      setCreatedIncident(null);
      setMessage(`${displayName(name)} is active.`);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function generateTraffic() {
    const generatedScenarioName = scenarios.find((scenario) => scenario.active)?.name ?? null;
    setBusy("traffic");
    setError("");
    setMessage("");
    setTrafficBatch(null);
    setTrafficScenarioName(null);
    setCreatedIncident(null);
    try {
      const result = await api.generateTraffic();
      setTrafficBatch(result);
      setTrafficScenarioName(generatedScenarioName);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function createInvestigation() {
    if (!trafficBatch) return;
    setBusy("incident");
    setError("");
    try {
      const presentation = incidentPresentationForScenario(trafficScenarioName);
      const incident = await api.createIncident(trafficBatch.traffic_batch_id, presentation);
      setCreatedIncident(incident);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function reset() {
    setBusy("reset");
    setError("");
    setMessage("");
    setTrafficBatch(null);
    setTrafficScenarioName(null);
    setCreatedIncident(null);
    try {
      await api.resetLab();
      setMessage("Lab reset to its clean baseline.");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Controlled evidence source</div>
          <h1>Incident Lab</h1>
          <p className="subtle">
            Inject controlled service behavior, generate observable evidence, and investigate the
            resulting incident.
          </p>
        </div>
        <div className="lab-header-actions">
          <button className="button" onClick={reset} disabled={Boolean(busy)}>
            <RotateCcw size={14} /> Reset
          </button>
          <button className="button primary" onClick={generateTraffic} disabled={Boolean(busy)}>
            <Send size={14} />
            {busy === "traffic" ? "Generating traffic…" : "Generate traffic"}
          </button>
        </div>
      </div>

      <div className="notice lab-boundary-notice">
        The Lab knows which scenario is active. TraceLens reasoning receives only logs, deployment
        records, and health checks — never scenario control state.
      </div>

      <LabLifecycle stages={lifecycle} />

      {busy === "traffic" && (
        <div className="lab-generating" role="status" aria-live="polite">
          <div>
            <strong>Generating real checkout traffic…</strong>
            <span>Waiting for the traffic request and exact batch identifier.</span>
          </div>
          <ActivityRail state="running" />
        </div>
      )}

      {error && <div className="error-box lab-feedback">{error}</div>}
      {message && <div className="lab-feedback subtle">{message}</div>}

      {trafficBatch && (
        <section className="panel lab-batch-panel">
          <div className="panel-head">
            <h2>Traffic batch</h2>
            <span className="badge healthy">Evidence captured</span>
          </div>
          <div className="lab-batch-content">
            <dl className="lab-summary-grid">
              <div><dt>Traffic batch</dt><dd className="mono">{trafficBatch.traffic_batch_id}</dd></div>
              <div><dt>Requests generated</dt><dd>{trafficBatch.requests}</dd></div>
              <div><dt>Failed</dt><dd>{failedTrafficRequests(trafficBatch.results)}</dd></div>
              <div><dt>Response mix</dt><dd className="mono">{Object.entries(trafficBatch.results).map(([status, count]) => `${status}: ${count}`).join(" · ")}</dd></div>
              <div><dt>Evidence</dt><dd className="lab-evidence-captured">Captured</dd></div>
              <div><dt>Created</dt><dd>{batchCreatedAt(trafficBatch.ended_at)}</dd></div>
            </dl>
            <div className="lab-batch-action">
              {createdIncident ? (
                <>
                  <span><CheckCircle2 size={14} /> Investigation created</span>
                  <Link className="button small" href={`/incidents/${createdIncident.id}`}>
                    Open investigation <ArrowRight size={13} />
                  </Link>
                </>
              ) : (
                <button
                  className="button primary"
                  onClick={createInvestigation}
                  disabled={Boolean(busy)}
                >
                  {busy === "incident" ? "Creating investigation…" : "Create investigation"}
                  <ArrowRight size={14} />
                </button>
              )}
            </div>
          </div>
        </section>
      )}

      <div className="lab-grid">
        <div className="scenario-grid">
          {scenarios.map((scenario) => (
            <article className={`panel scenario ${scenario.active ? "active" : ""}`} key={scenario.name}>
              <div className="scenario-top">
                <h2>{displayName(scenario.name)}</h2>
                {scenario.active && <span className="badge healthy">Active</span>}
              </div>
              <p>{scenario.description}</p>
              <button
                className="button small"
                disabled={scenario.active || Boolean(busy)}
                onClick={() => activate(scenario.name)}
              >
                {busy === scenario.name ? "Activating…" : scenario.active ? "Active" : "Activate"}
              </button>
            </article>
          ))}
        </div>

        <div className="lab-side-stack">
          {activeExperiment && (
            <aside className="panel lab-experiment">
              <div className="panel-head">
                <h2>Active experiment</h2>
                <span className="badge healthy">Active</span>
              </div>
              <dl>
                <div><dt>Scenario</dt><dd>{displayName(activeExperiment.name)}</dd></div>
                <div><dt>Injected behavior</dt><dd>{activeExperiment.description}</dd></div>
                <div><dt>Affected service</dt><dd className="mono">payment-service</dd></div>
                <div><dt>Expected observation</dt><dd>{activeExperiment.expected_behavior}</dd></div>
              </dl>
            </aside>
          )}

          <aside className="panel">
            <div className="panel-head">
              <h2>Service health</h2>
              <Activity size={14} color="var(--text-tertiary)" />
            </div>
            {health.length ? (
              health.map((item) => (
                <div className="health-row" key={item.service}>
                  <div className="health-copy">
                    <div>{item.service}</div>
                    <div className="metric-note mono">
                      {item.deployment_version ? `Version ${item.deployment_version}` : "Version unavailable"}
                    </div>
                    {typeof item.available_connections === "number" && (
                      <div className="metric-note">Available connections: {item.available_connections}</div>
                    )}
                    {typeof item.provider_configured === "boolean" && (
                      <div className={`metric-note ${item.provider_configured ? "" : "health-warning"}`}>
                        Provider configured: {item.provider_configured ? "yes" : "no"}
                      </div>
                    )}
                  </div>
                  <StatusBadge value={item.status} />
                </div>
              ))
            ) : (
              <div className="empty health-empty">
                <div><strong>Services offline</strong>Start both lab processes.</div>
              </div>
            )}
          </aside>
        </div>
      </div>

      <div className="lab-wavefield">
        <TraceWavefield />
      </div>
    </>
  );
}
