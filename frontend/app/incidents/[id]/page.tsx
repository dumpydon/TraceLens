"use client";

import { use, useEffect, useMemo, useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import { API_BASE, api } from "@/lib/api";
import type { EvidenceItem, Incident, InvestigationEvent, Report } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { InvestigationFlow } from "@/components/investigation-flow";
import { EventTimeline } from "@/components/event-timeline";
import { EvidencePanel } from "@/components/evidence-panel";
import { ReportPanel } from "@/components/report-panel";

export default function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const latest = events.at(-1);
  const completed = latest?.event_type === "investigation_completed";
  const refinements = events.filter((item) => item.event_type === "investigation_refined").length;

  useEffect(() => {
    api.incident(id).then(setIncident).catch((err) => setError(err.message));
    api.report(id).then(setReport).catch(() => undefined);
    api.evidence(id).then(setEvidence).catch(() => undefined);
  }, [id]);

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/api/incidents/${id}/events`);
    const names = ["investigation_started", "context_collection_started", "logs_collected", "deployment_found", "runtime_analysis_completed", "retrieval_started", "documents_retrieved", "hypothesis_generated", "verification_started", "verification_completed", "investigation_refined", "report_generated", "investigation_completed", "investigation_failed"];
    const handler = (message: MessageEvent) => {
      const event = JSON.parse(message.data) as InvestigationEvent;
      setEvents((current) => current.some((item) => item.id === event.id) ? current : [...current, event]);
      if (event.event_type === "documents_retrieved" || event.event_type === "report_generated") api.evidence(id).then(setEvidence).catch(() => undefined);
      if (event.event_type === "report_generated") api.report(id).then(setReport).catch(() => undefined);
      if (event.event_type === "investigation_completed" || event.event_type === "investigation_failed") api.incident(id).then(setIncident).catch(() => undefined);
    };
    names.forEach((name) => source.addEventListener(name, handler));
    // Native EventSource retry is important when the free demo backend is waking up.
    source.onerror = () => undefined;
    return () => source.close();
  }, [id]);

  async function investigate() {
    setStarting(true); setError("");
    try { await api.investigate(id); setIncident((item) => item ? { ...item, status: "investigating" } : item); }
    catch (err) { setError((err as Error).message); }
    finally { setStarting(false); }
  }

  const status = useMemo(() => incident?.status ?? "open", [incident]);
  if (!incident && !error) return <div className="loading-line" />;
  return <>{error && <div className="error-box" style={{ marginBottom: 14 }}>{error}</div>}<div className="page-head"><div><div className="eyebrow mono">{id}</div><h1>{incident?.title ?? "Incident unavailable"}</h1><p className="subtle">{incident?.summary}</p></div><div style={{ display: "flex", gap: 8, alignItems: "center" }}><StatusBadge value={status} />{status === "open" && <button className="button primary" onClick={investigate} disabled={starting}><Play size={14} />{starting ? "Starting…" : "Start investigation"}</button>}{status === "failed" && <button className="button" onClick={investigate}><RefreshCw size={14} /> Retry</button>}</div></div><section className="panel" style={{ marginBottom: 14 }}><InvestigationFlow stage={latest?.stage} status={status} refinements={refinements} completed={completed} /></section><div className="detail-grid"><div className="detail-main"><section className="panel"><div className="panel-head"><h2>Investigation timeline</h2><span className="env-chip">SSE live</span></div><EventTimeline events={events} /></section><section className="panel report"><div className="panel-head"><h2>Root-cause report</h2>{report && <StatusBadge value={report.root_cause_category} />}</div><ReportPanel report={report} /></section></div><aside className="detail-side"><section className="panel"><div className="panel-head"><h2>Evidence</h2><span className="env-chip">{evidence.length} items</span></div><EvidencePanel evidence={evidence} /></section></aside></div></>;
}
