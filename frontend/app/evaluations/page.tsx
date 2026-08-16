"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Evaluation } from "@/lib/types";
import { formatPercent, formatRelativeTime } from "@/lib/format";

export default function EvaluationsPage() {
  const [runs, setRuns] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => { api.evaluations().then(setRuns).catch((err) => setError(err.message)).finally(() => setLoading(false)); }, []);
  return <><div className="page-head"><div><div className="eyebrow">Offline benchmark</div><h1>Evaluations</h1><p className="subtle">Reproducible Incident Lab cases measured with deterministic checks and optional semantic judging.</p></div></div>{error && <div className="error-box">{error}</div>}{loading ? <div className="loading-line" /> : <section className="panel">{runs.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Run</th><th>Examples</th><th>Root cause</th><th>Service</th><th>Retrieval</th><th>Groundedness</th><th>Created</th></tr></thead><tbody>{runs.map((run) => <tr key={run.id}><td className="primary-cell mono">{run.id}</td><td>{run.examples}</td><td>{formatPercent(run.root_cause_correctness)}</td><td>{formatPercent(run.affected_service_correctness)}</td><td>{formatPercent(run.retrieval_relevance)}</td><td>{formatPercent(run.evidence_groundedness)}</td><td>{formatRelativeTime(run.created_at)}</td></tr>)}</tbody></table></div> : <div className="empty"><div><strong>No evaluation runs yet</strong>Run <span className="mono">make eval</span> after generating the benchmark incidents.</div></div>}</section>}</>;
}

