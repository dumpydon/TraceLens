"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Incident } from "@/lib/types";
import { IncidentTable } from "@/components/incident-table";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const router = useRouter();
  useEffect(() => { api.incidents().then(setIncidents).catch((err) => setError(err.message)).finally(() => setLoading(false)); }, []);
  async function create() { try { const incident = await api.createIncident(); router.push(`/incidents/${incident.id}`); } catch (err) { setError((err as Error).message); } }
  return <><div className="page-head"><div><div className="eyebrow">Incident registry</div><h1>Incidents</h1><p className="subtle">Investigations are scoped to a stable incident ID and durable checkpoint thread.</p></div><button className="button primary" onClick={create}><Plus size={14} /> Create incident</button></div>{error && <div className="error-box">{error}</div>}{loading ? <div className="loading-line" /> : <section className="panel"><IncidentTable incidents={incidents} /></section>}</>;
}

