"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, Plus, RotateCcw, Send } from "lucide-react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Scenario } from "@/lib/types";
import { ActivityRail, type ActivityRailState } from "@/components/activity-rail";
import { StatusBadge } from "@/components/status-badge";
import { TraceWavefield } from "@/components/visuals/trace-wavefield";

export default function LabPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [health, setHealth] = useState<{ service: string; status: string; deployment_version?: string }[]>([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [trafficBatchId, setTrafficBatchId] = useState<string | null>(null);
  const [trafficFailed, setTrafficFailed] = useState(false);
  const router = useRouter();
  const load = useCallback(() => Promise.all([api.scenarios().then(setScenarios), api.labHealth().then(setHealth)]).catch((err) => setError(err.message)), []);
  useEffect(() => { load(); const timer = setInterval(load, 5000); return () => clearInterval(timer); }, [load]);
  async function activate(name: string) { setBusy(name); setError(""); setTrafficFailed(false); try { await api.activateScenario(name); setTrafficBatchId(null); setMessage(`${name.replaceAll("_", " ")} is active.`); await load(); } catch (err) { setError((err as Error).message); } finally { setBusy(""); } }
  async function traffic() { setBusy("traffic"); setError(""); setTrafficBatchId(null); setTrafficFailed(false); try { const result = await api.generateTraffic(); setTrafficBatchId(result.traffic_batch_id); setMessage(`Generated ${result.requests} checkouts · ${Object.entries(result.results).map(([key, count]) => `${key}: ${count}`).join(" · ")}`); await load(); } catch (err) { setTrafficFailed(true); setError((err as Error).message); } finally { setBusy(""); } }
  async function createIncident() { if (!trafficBatchId) return; setBusy("incident"); setError(""); try { const incident = await api.createIncident(trafficBatchId); router.push(`/incidents/${incident.id}`); } catch (err) { setError((err as Error).message); setBusy(""); } }
  async function reset() { setBusy("reset"); setError(""); setTrafficBatchId(null); setTrafficFailed(false); try { await api.resetLab(); setMessage("Lab reset to baseline and runtime logs cleared."); await load(); } catch (err) { setError((err as Error).message); } finally { setBusy(""); } }
  const trafficActivity: ActivityRailState = trafficBatchId ? "completed" : busy === "traffic" ? "running" : trafficFailed ? "failed" : "idle";
  return <><div className="page-head"><div><div className="eyebrow">Controlled evidence source</div><h1>Incident Lab</h1><p className="subtle">Activate a deterministic service behavior, generate real HTTP traffic, then investigate its observable evidence.</p></div><div style={{ display: "flex", gap: 8 }}><button className="button" onClick={reset} disabled={!!busy}><RotateCcw size={14} /> Reset</button><button className="button primary" onClick={traffic} disabled={!!busy}><Send size={14} /> {busy === "traffic" ? "Generating…" : "Generate traffic"}</button></div></div><div className="notice" style={{ marginBottom: 14 }}>The lab controller knows which scenario is active. TraceLens receives only logs, deployment records, and health checks—never this control state during reasoning.</div><div className="lab-traffic-activity"><ActivityRail state={trafficActivity} /></div>{error && <div className="error-box" style={{ marginBottom: 14 }}>{error}</div>}{message && <div className="panel-body subtle" style={{ paddingLeft: 0, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}><span>{message}</span>{trafficBatchId && <button className="button primary" onClick={createIncident} disabled={!!busy}><Plus size={14} /> {busy === "incident" ? "Creating…" : "Create incident"}</button>}</div>}<div className="lab-grid"><div className="scenario-grid">{scenarios.map((scenario) => <article className={`panel scenario ${scenario.active ? "active" : ""}`} key={scenario.name}><div className="scenario-top"><h2>{scenario.name.replaceAll("_", " ")}</h2>{scenario.active && <StatusBadge value="healthy" />}</div><p>{scenario.description}</p><button className="button small" disabled={scenario.active || !!busy} onClick={() => activate(scenario.name)}>{busy === scenario.name ? "Activating…" : scenario.active ? "Active" : "Activate"}</button></article>)}</div><aside className="panel"><div className="panel-head"><h2>Service health</h2><Activity size={14} color="var(--text-tertiary)" /></div>{health.length ? health.map((item) => <div className="health-row" key={item.service}><div><div>{item.service}</div><div className="metric-note mono">{item.deployment_version ?? "unavailable"}</div></div><StatusBadge value={item.status} /></div>) : <div className="empty"><div><strong>Services offline</strong>Start both lab processes.</div></div>}</aside></div><TraceWavefield /></>;
}
