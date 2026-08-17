"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { Check, CircleHelp, Play, X } from "lucide-react";
import { api } from "@/lib/api";
import type {
  Evaluation,
  EvaluationCaseResult,
  EvaluationRunStatus,
} from "@/lib/types";
import { formatPercent, formatRelativeTime } from "@/lib/format";
import { EvaluationRunningState } from "@/components/evaluation-running-state";

const METRICS = [
  {
    key: "root_cause_correctness",
    label: "Root Cause Accuracy",
    help: "Was the diagnosed failure category correct?",
  },
  {
    key: "affected_service_correctness",
    label: "Service Accuracy",
    help: "Was the affected/root-cause service identified correctly?",
  },
  {
    key: "retrieval_relevance",
    label: "Retrieval Relevance",
    help: "Did retrieval surface the expected operational evidence?",
  },
  {
    key: "evidence_groundedness",
    label: "Evidence Groundedness",
    help: "Are report claims supported by resolvable collected evidence?",
  },
] as const;

function caseLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function ResultMark({ score }: { score: number }) {
  const passed = score === 1;
  return (
    <span className={`evaluation-result ${passed ? "pass" : "fail"}`}>
      {passed ? <Check size={13} /> : <X size={13} />}
      {passed ? "Pass" : "Fail"}
    </span>
  );
}

function CaseDetail({ result }: { result: EvaluationCaseResult }) {
  return (
    <div className="evaluation-case-detail">
      <div>
        <span>Root cause</span>
        <small>Expected</small>
        <strong>{result.expected_root_cause_category}</strong>
        <small>Predicted</small>
        <strong>{result.predicted_root_cause_category}</strong>
      </div>
      <div>
        <span>Service</span>
        <small>Expected</small>
        <strong>{result.expected_affected_service}</strong>
        <small>Predicted</small>
        <strong>{result.predicted_affected_service}</strong>
      </div>
      <div>
        <span>Expected evidence</span>
        <strong>{result.expected_evidence.join(", ") || "None specified"}</strong>
        <span>Retrieved failure types</span>
        <strong>{result.retrieved_failure_types.join(", ") || "None"}</strong>
      </div>
      <div>
        <span>Retrieved documents</span>
        <strong>{result.retrieved_evidence_ids.join(", ") || "None"}</strong>
        <span>Resolvable citations</span>
        <strong>
          {result.citation_ids.length}/{result.available_evidence_ids.length} cited/available
        </strong>
      </div>
    </div>
  );
}

export default function EvaluationsPage() {
  const [runs, setRuns] = useState<Evaluation[]>([]);
  const [runStatus, setRunStatus] = useState<EvaluationRunStatus | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [expandedCase, setExpandedCase] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.evaluations(), api.evaluationStatus()])
      .then(([evaluationRuns, status]) => {
        setRuns(evaluationRuns);
        setRunStatus(status);
        setSelectedRunId(evaluationRuns[0]?.id ?? null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (runStatus?.status !== "running") return;
    const timer = window.setInterval(async () => {
      try {
        const nextStatus = await api.evaluationStatus();
        setRunStatus(nextStatus);
        if (nextStatus.status === "completed") {
          const evaluationRuns = await api.evaluations();
          setRuns(evaluationRuns);
          setSelectedRunId(nextStatus.run_id ?? evaluationRuns[0]?.id ?? null);
        } else if (nextStatus.status === "failed") {
          setError(nextStatus.error ?? "Evaluation run failed.");
        }
      } catch (err) {
        setError((err as Error).message);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [runStatus?.status]);

  const latest = runs[0] ?? null;
  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? null,
    [runs, selectedRunId],
  );
  const running = runStatus?.status === "running";

  async function runEvaluation() {
    setError("");
    setExpandedCase(null);
    setRunStatus({ status: "running", run_id: null, error: null });
    try {
      setRunStatus(await api.runEvaluation());
    } catch (err) {
      setRunStatus({ status: "failed", run_id: null, error: (err as Error).message });
      setError((err as Error).message);
    }
  }

  return (
    <>
      <div className="page-head evaluation-head">
        <div>
          <div className="eyebrow">Offline benchmark</div>
          <h1>Evaluations</h1>
          <p className="subtle">
            Benchmark TraceLens against reproducible incidents with known ground truth.
          </p>
          <p className="evaluation-explanation">
            Evaluation runs execute the investigation pipeline against fixed benchmark cases and
            score diagnosis accuracy, service attribution, retrieval quality, and evidence
            groundedness.
          </p>
        </div>
        <button className="button primary" onClick={runEvaluation} disabled={running}>
          <Play size={14} />
          {running ? "Running evaluation…" : "Run evaluation"}
        </button>
      </div>

      {error && <div className="error-box evaluation-error">{error}</div>}
      {running && <EvaluationRunningState />}
      {loading && <div className="loading-line" />}

      {!loading && latest && (
        <div className="metric-grid evaluation-metrics">
          {METRICS.map((metric) => (
            <div className="metric" key={metric.key}>
              <div className="metric-label evaluation-metric-label" title={metric.help}>
                {metric.label}
                <CircleHelp size={12} aria-label={metric.help} />
              </div>
              <div className="metric-value">{formatPercent(latest[metric.key])}</div>
              <div className="metric-note">Latest run</div>
            </div>
          ))}
        </div>
      )}

      {!loading && !runs.length && (
        <section className="panel">
          <div className="empty evaluation-empty">
            <div>
              <strong>No evaluation runs yet.</strong>
              <p>
                Run the benchmark to measure TraceLens against reproducible incidents with known
                ground truth.
              </p>
              <button className="button primary" onClick={runEvaluation} disabled={running}>
                <Play size={14} />
                {running ? "Running evaluation…" : "Run evaluation"}
              </button>
            </div>
          </div>
        </section>
      )}

      {!loading && runs.length > 0 && (
        <section className="panel evaluation-history">
          <div className="panel-head">
            <h2>Evaluation history</h2>
            <span className="metric-note">Newest first</span>
          </div>
          <div className="table-wrap">
            <table className="data-table evaluation-runs-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Cases</th>
                  <th>Root cause</th>
                  <th>Service</th>
                  <th>Retrieval</th>
                  <th>Groundedness</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    className={selectedRunId === run.id ? "selected" : ""}
                    key={run.id}
                    onClick={() => {
                      setSelectedRunId(run.id);
                      setExpandedCase(null);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedRunId(run.id);
                        setExpandedCase(null);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <td className="primary-cell mono">{run.id}</td>
                    <td>{run.examples}</td>
                    <td>{formatPercent(run.root_cause_correctness)}</td>
                    <td>{formatPercent(run.affected_service_correctness)}</td>
                    <td>{formatPercent(run.retrieval_relevance)}</td>
                    <td>{formatPercent(run.evidence_groundedness)}</td>
                    <td>{formatRelativeTime(run.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedRun && (
            <div className="evaluation-run-detail">
              <div className="evaluation-detail-head">
                <div>
                  <div className="eyebrow">Selected run</div>
                  <h2 className="mono">{selectedRun.id}</h2>
                </div>
                <span className="subtle">{selectedRun.examples} benchmark cases</span>
              </div>

              {selectedRun.case_results.length ? (
                <div className="table-wrap">
                  <table className="data-table evaluation-cases-table">
                    <thead>
                      <tr>
                        <th>Case</th>
                        <th>Root cause</th>
                        <th>Service</th>
                        <th>Retrieval</th>
                        <th>Grounded</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedRun.case_results.map((result) => (
                        <Fragment key={result.case_name}>
                          <tr
                            className="evaluation-case-row"
                            onClick={() =>
                              setExpandedCase((current) =>
                                current === result.case_name ? null : result.case_name,
                              )
                            }
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                setExpandedCase((current) =>
                                  current === result.case_name ? null : result.case_name,
                                );
                              }
                            }}
                            role="button"
                            tabIndex={0}
                          >
                            <td className="primary-cell">{caseLabel(result.case_name)}</td>
                            <td><ResultMark score={result.root_cause_correctness} /></td>
                            <td><ResultMark score={result.affected_service_correctness} /></td>
                            <td><ResultMark score={result.retrieval_relevance} /></td>
                            <td><ResultMark score={result.evidence_groundedness} /></td>
                          </tr>
                          {expandedCase === result.case_name && (
                            <tr className="evaluation-case-expanded">
                              <td colSpan={5}><CaseDetail result={result} /></td>
                            </tr>
                          )}
                        </Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="evaluation-legacy-note">
                  Case-level results were not stored for this legacy run. Aggregate metrics remain
                  available above.
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </>
  );
}
