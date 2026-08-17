import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { BackendStartupPanel } from "./backend-startup-panel";
import { SystemBriefingContent } from "./system-briefing";

describe("SystemBriefing", () => {
  it("renders complete architecture content without backend data", () => {
    const html = renderToStaticMarkup(<SystemBriefingContent runtimeStatus="waking" />);
    expect(html).toContain("How TraceLens investigates an incident");
    expect(html).toContain("TraceLens is an AI-powered incident investigation lab.");
    expect(html).toContain("understand what went wrong using A LangGraph workflow coordinates the investigation");
    expect(html).toContain("RAG retrieves relevant operational knowledge to help interpret the evidence.");
    const technologyStripIndex = html.indexOf('class="briefing-technology-line mono"');
    expect(technologyStripIndex).toBeGreaterThan(html.indexOf("produces an evidence-backed diagnosis"));
    expect(html.indexOf("Evidence-first investigation")).toBeGreaterThan(technologyStripIndex);
    expect(html.match(/briefing-technology-line/g)).toHaveLength(1);
    expect(html).toContain("LangSmith</span><span>Pydantic</span><span>FastAPI");
    expect(html).toContain("Evidence-first investigation");
    expect(html).toContain("The investigator is never told which failure was injected.");
    expect(html).toContain("root cause from logs, service health, deployment signals");
    expect(html).toContain("Controlled Incident Lab");
    expect(html).toContain("Checkout");
    expect(html).toContain("Payment");
    expect(html).toContain("Runtime evidence");
    expect(html).toContain("LangGraph Investigator");
    expect(html).toContain("Hypothesize");
    expect(html).toContain("insufficient evidence");
    expect(html).toContain("Verified report");
    expect(html).toContain("Bounded agentic investigation");
    expect(html).toContain("LangGraph runs the investigation as a stateful workflow with checkpointed execution.");
    expect(html).toContain("Insufficient evidence → Retrieve → Hypothesize → Verify again");
    expect(html).not.toContain("Checkpointed state makes investigations resumable by incident thread.");
    expect(html).toContain("Operational RAG");
    expect(html).toContain("Evidence verification");
    expect(html).toContain("Runtime evidence guides retrieval of relevant runbooks");
    expect(html).toContain("Hypothesis → Verify → Report");
    expect(html).not.toContain("Knowledge with a purpose");
    expect(html).not.toContain("Hypothesis before conclusion");
    expect(html).not.toContain("Evidence verification determines whether support is sufficient.");
    expect(html).toContain("LangSmith tracing");
    expect(html).toContain("Evaluation harness");
    expect(html).not.toContain("Checkpointed state");
    expect(html).not.toContain("Human approval remains a future extension");
    expect(html).toContain("Separated runtime boundaries");
    expect(html).toContain("Supabase PostgreSQL");
    expect(html).toContain("REST + SSE");
    expect(html).toContain("Models / embeddings");
    expect(html).toContain("Persistent state");
    expect(html).toContain("not calibrated");
    expect(html).toContain("Waiting for investigation runtime");
    expect(html).not.toContain("href=\"/lab\"");
    expect(html).not.toContain("Why these technologies?");
    expect(html).not.toContain("Evidence confidence");
    expect(html).not.toContain("Inject failure</strong>");
    expect(html).not.toContain("Investigate from evidence");
    expect(html).not.toContain(">Reasoning boundary<");
    expect(html).not.toContain(">System briefing<");
    expect(html).not.toContain(">What TraceLens is<");
    expect(html).not.toContain(">Investigation architecture<");
    expect(html).not.toContain('<div class="eyebrow">LangGraph</div>');
    expect(html).not.toContain(">Structured verification<");
    expect(html).not.toContain(">Explore TraceLens<");
    expect(html).not.toContain(">Regression safety<");
    expect(html).not.toContain(">Durable execution<");
    expect(html).not.toContain(">Hosted demo<");
  });

  it("enables product calls to action when the runtime is ready", () => {
    const html = renderToStaticMarkup(<SystemBriefingContent runtimeStatus="ready" />);
    expect(html).toContain("href=\"/lab\"");
    expect(html).toContain("href=\"/evaluations\"");
    expect(html).not.toContain("Waiting for investigation runtime");
  });
});

describe("BackendStartupPanel", () => {
  it("uses accurate hosted waking and long-wait copy", () => {
    const waking = renderToStaticMarkup(
      <BackendStartupPanel status="waking" isLocal={false} />,
    );
    expect(waking).toContain("free hosted backend");
    expect(waking).toContain("Usually ready within 1–2 minutes");
    expect(waking).not.toContain("countdown");

    const longWait = renderToStaticMarkup(
      <BackendStartupPanel status="long_wait" isLocal={false} onRetry={() => undefined} />,
    );
    expect(longWait).toContain("taking longer than expected");
    expect(longWait).toContain("Retry connection");
  });

  it("does not describe a missing localhost API as a hosted cold start", () => {
    const html = renderToStaticMarkup(<BackendStartupPanel status="waking" isLocal />);
    expect(html).toContain("local API");
    expect(html).not.toContain("free hosted backend");
  });
});
