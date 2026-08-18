"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, CircleDot, FlaskConical, Target } from "lucide-react";
import { api } from "@/lib/api";
import type { Incident } from "@/lib/types";
import { formatPercent } from "@/lib/format";
import { IncidentTable } from "@/components/incident-table";
import { TraceConvergence } from "@/components/visuals/trace-convergence";
import { TECHNOLOGIES, TechnologyStrip } from "@/components/technology-strip";

const OVERVIEW_TECHNOLOGIES = [
  ...TECHNOLOGIES.slice(0, 6),
  "Next.js",
  ...TECHNOLOGIES.slice(6),
] as const;

type Overview = { active_incidents: number; resolved_incidents: number; recent_incidents: Incident[]; latest_evaluation_score: number | null };

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api.overview().then(setData).catch((err) => setError(err.message)); }, []);
  return (
    <div className="overview-page">
      <div className="page-head"><div><div className="eyebrow">Operational workspace</div><h1>Investigation overview</h1><p className="subtle">Current incident workload and evidence-backed investigation outcomes.</p></div><Link className="button" href="/lab"><FlaskConical size={14} /> Open Incident Lab</Link></div>
      {error && <div className="error-box">Backend unavailable: {error}</div>}
      {!data && !error && <div className="loading-line" />}
      {data && <>
        <div className="metric-grid">
          <div className="metric"><div className="metric-label"><CircleDot size={13} /> Active investigations</div><div className="metric-value">{data.active_incidents}</div><div className="metric-note">Persisted investigation state</div></div>
          <div className="metric"><div className="metric-label"><CheckCircle2 size={13} /> Resolved incidents</div><div className="metric-value">{data.resolved_incidents}</div><div className="metric-note">Reports with resolvable citations</div></div>
          <div className="metric"><div className="metric-label"><Target size={13} /> Latest evaluation</div><div className="metric-value">{data.latest_evaluation_score === null ? "—" : formatPercent(data.latest_evaluation_score)}</div><div className="metric-note">Average of four V1 measures</div></div>
          <div className="metric"><div className="metric-label">Evidence policy</div><div className="metric-value" style={{ fontSize: 18 }}>Strict</div><div className="metric-note">Unknown citations are rejected</div></div>
        </div>
        <section className="panel"><div className="panel-head"><h2>Recent incidents</h2><Link href="/incidents" className="button small">View all <ArrowRight size={13} /></Link></div><IncidentTable incidents={data.recent_incidents} startedColumnPosition="third" /></section>
        <TraceConvergence />
        <TechnologyStrip className="overview-technology-line" technologies={OVERVIEW_TECHNOLOGIES} />
      </>}
    </div>
  );
}
