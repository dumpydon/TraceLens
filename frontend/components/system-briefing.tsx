"use client";

import Link from "next/link";
import {
  Activity,
  ArrowDown,
  ArrowRight,
  CheckCircle2,
  GitBranch,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import type { BackendRuntimeStatus } from "../lib/backend-runtime";
import { useBackendRuntime } from "./backend-runtime-provider";
import { TechnologyStrip } from "./technology-strip";

const EXECUTION_STAGES = ["Load", "Context", "Analyze", "Retrieve", "Hypothesis", "Verify", "Report"];
const REASONING_PHASES = ["Analyze", "Retrieve", "Hypothesize", "Verify"];

export function SystemBriefingContent({
  runtimeStatus,
}: {
  runtimeStatus: BackendRuntimeStatus;
}) {
  const ready = runtimeStatus === "ready";

  return (
    <article className="system-briefing">
      <header className="briefing-header">
        <h1>How TraceLens investigates an incident</h1>
        <p>
          <strong>TraceLens is an AI-powered incident investigation lab.</strong> It recreates
          realistic service failures—such as payment latency, payment failures, connection
          exhaustion, and bad deployments—and generates the runtime evidence those failures would
          produce.
        </p>
        <p className="briefing-header-primary-copy">
          TraceLens analyzes the resulting logs, service health, deployment data, and other runtime
          signals to understand what went wrong using A LangGraph workflow coordinates the
          investigation, while RAG retrieves relevant operational knowledge to help interpret the
          evidence.
        </p>
        <p>
          TraceLens then forms a root-cause hypothesis, verifies it against the available evidence,
          and produces an evidence-backed diagnosis with citations and a support score.
        </p>
        <TechnologyStrip />
      </header>

      <div className="briefing-layout">
        <main className="briefing-main">
          <section className="briefing-section briefing-introduction">
            <div className="briefing-section-heading">
              <span className="briefing-index mono">01</span>
              <div>
                <h2>Evidence-first investigation</h2>
              </div>
            </div>
            <aside className="trust-boundary-note">
              <ShieldCheck size={16} aria-hidden="true" />
              <div>
                <strong>The investigator is never told which failure was injected.</strong>
                <p>
                  It must infer the root cause from logs, service health, deployment signals, and
                  retrieved operational knowledge.
                </p>
              </div>
            </aside>
          </section>

          <section className="briefing-section briefing-topology-section">
            <div className="briefing-section-heading">
              <span className="briefing-index mono">02</span>
              <div>
                <h2>Evidence to verified diagnosis</h2>
              </div>
            </div>

            <div className="investigation-topology" aria-label="TraceLens investigation architecture">
              <div className="topology-lab topology-zone">
                <div className="topology-zone-label mono">
                  <Activity size={12} aria-hidden="true" /> Controlled Incident Lab
                </div>
                <div className="topology-services">
                  <div className="topology-service">
                    <span className="mono">SERVICE / 01</span>
                    <strong>Checkout</strong>
                  </div>
                  <div className="topology-service">
                    <span className="mono">SERVICE / 02</span>
                    <strong>Payment</strong>
                  </div>
                </div>
              </div>

              <div className="topology-connector" aria-hidden="true"><ArrowDown size={13} /></div>

              <div className="topology-evidence topology-zone">
                <div>
                  <span className="mono">Runtime evidence</span>
                  <strong>Observable system state</strong>
                </div>
                <p className="mono">Logs · Health · Deployments</p>
              </div>

              <div className="topology-connector" aria-hidden="true"><ArrowDown size={13} /></div>

              <div className="topology-investigator topology-zone">
                <div className="topology-investigator-heading">
                  <div>
                    <span className="mono">Stateful reasoning boundary</span>
                    <strong>LangGraph Investigator</strong>
                  </div>
                  <GitBranch size={17} aria-hidden="true" />
                </div>
                <div className="topology-phases">
                  {REASONING_PHASES.map((phase, index) => (
                    <div className={phase === "Verify" ? "topology-phase verify" : "topology-phase"} key={phase}>
                      <span className="mono">0{index + 1}</span>
                      <strong>{phase}</strong>
                    </div>
                  ))}
                </div>
                <div className="topology-feedback">
                  <RotateCcw size={12} aria-hidden="true" />
                  <span className="mono">insufficient evidence</span>
                  <b>Verify → Retrieve</b>
                </div>
              </div>

              <div className="topology-connector topology-connector-verified" aria-hidden="true">
                <ArrowDown size={13} />
              </div>

              <div className="topology-report topology-zone">
                <CheckCircle2 size={18} aria-hidden="true" />
                <div>
                  <span className="mono">Verified report</span>
                  <strong>Root cause · Citations · Support score</strong>
                </div>
              </div>
            </div>
            <p className="topology-support-note">
              Support score reflects evidence corroboration and verification — not calibrated
              probability.
            </p>
          </section>

          <section className="briefing-section briefing-langgraph">
            <div className="briefing-section-heading">
              <span className="briefing-index mono">03</span>
              <div>
                <h2>Bounded agentic investigation</h2>
              </div>
            </div>
            <p className="briefing-section-copy">
              LangGraph runs the investigation as a stateful workflow with checkpointed execution.
            </p>
            <ol className="execution-trace" aria-label="LangGraph execution stages">
              {EXECUTION_STAGES.map((stage) => <li key={stage}>{stage}</li>)}
            </ol>
            <div className="verification-loop-strip">
              <RotateCcw size={12} aria-hidden="true" />
              <span className="mono">Insufficient evidence → Retrieve → Hypothesize → Verify again</span>
            </div>
          </section>

          <div className="briefing-technical-strip">
            <section className="briefing-technical-column rag-module">
              <h2>Operational RAG</h2>
              <p>Runtime evidence guides retrieval of relevant runbooks and architecture knowledge.</p>
              <div className="technical-footer mono">Embeddings · MMR retrieval · Runbooks</div>
            </section>
            <section className="briefing-technical-column verification-module">
              <h2>Evidence verification</h2>
              <p>TraceLens proposes a root cause, then verifies it against runtime evidence before reporting it.</p>
              <div className="technical-footer mono">Hypothesis → Verify → Report</div>
            </section>
          </div>

        </main>

        <aside className="briefing-rail" aria-label="Supporting engineering capabilities">
          <section className="briefing-rail-module">
            <div className="briefing-rail-heading">
              <div className="eyebrow">Observability</div>
              <h2>LangSmith tracing</h2>
            </div>
            <p>Graph execution, model calls, retrieval, latency, and evaluation runs remain inspectable.</p>
            <div className="rail-metadata mono">Graph · Models · Retrieval · Latency</div>
          </section>

          <section className="briefing-rail-module rail-title-only">
            <h2>Evaluation harness</h2>
            <p>
              Reproducible incidents test root-cause, service, retrieval, and evidence-grounding behavior.
            </p>
            <div className="evaluation-labels mono">
              <span>Root cause</span><span>Service</span><span>Retrieval</span><span>Grounding</span>
            </div>
          </section>

          <section className="briefing-rail-module rail-title-only hosted-runtime-module">
            <h2>Separated runtime boundaries</h2>
            <div className="hosted-topology hosted-dag" aria-label="TraceLens hosted runtime architecture">
              <div className="hosted-node hosted-dag-root">
                <span className="mono">Vercel</span>
                <strong>Next.js interface</strong>
              </div>
              <div className="hosted-dag-link mono">
                <ArrowDown size={12} aria-hidden="true" />
                <span>REST + SSE</span>
                <i className="hosted-flow-particle hosted-flow-particle--down" aria-hidden="true" />
              </div>
              <div className="hosted-node hosted-backend hosted-dag-root">
                <span className="mono">Render</span>
                <strong>FastAPI · LangGraph · Incident Lab</strong>
              </div>
              <div className="hosted-dag-fanout" aria-hidden="true">
                <i className="hosted-flow-particle hosted-flow-particle--fanout" />
              </div>
              <div className="hosted-dag-branches" aria-label="Render service dependencies">
                <div className="hosted-dag-branch">
                  <span className="hosted-dag-edge-label mono">Models / embeddings</span>
                  <i className="hosted-flow-particle hosted-flow-particle--branch" aria-hidden="true" />
                  <div className="hosted-node"><span className="mono">OpenAI</span><strong>Models</strong></div>
                </div>
                <div className="hosted-dag-branch">
                  <span className="hosted-dag-edge-label mono">Tracing</span>
                  <i className="hosted-flow-particle hosted-flow-particle--branch" aria-hidden="true" />
                  <div className="hosted-node"><span className="mono">LangSmith</span><strong>Tracing</strong></div>
                </div>
                <div className="hosted-dag-branch">
                  <span className="hosted-dag-edge-label mono">Persistent state</span>
                  <i className="hosted-flow-particle hosted-flow-particle--branch" aria-hidden="true" />
                  <div className="hosted-node hosted-database"><span className="mono">Supabase PostgreSQL</span><strong>Incidents · checkpoints · runtime state</strong></div>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </div>

      <footer className="briefing-product-cta">
        <div>
          <h2>Run the investigation yourself</h2>
          <p>
            Inject a controlled failure and watch TraceLens build, retrieve, verify, and report from
            runtime evidence.
          </p>
        </div>
        <div className="briefing-product-actions">
          {ready ? (
            <>
              <Link className="button primary" href="/lab">
                Open Incident Lab <ArrowRight size={14} />
              </Link>
              <Link className="button" href="/evaluations">View evaluations</Link>
            </>
          ) : (
            <button className="button primary" disabled>Waiting for investigation runtime…</button>
          )}
        </div>
      </footer>
    </article>
  );
}

export function SystemBriefing() {
  const { status } = useBackendRuntime();
  return <SystemBriefingContent runtimeStatus={status} />;
}
