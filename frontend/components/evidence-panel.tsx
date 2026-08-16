import type { EvidenceItem } from "@/lib/types";

export function EvidencePanel({ evidence }: { evidence: EvidenceItem[] }) {
  if (!evidence.length) return <div className="empty"><div><strong>No evidence loaded</strong>Evidence appears after context collection.</div></div>;
  return <div className="evidence-list">{evidence.map((item) => <details className="evidence-row" key={item.id}><summary><span className="evidence-kind">{item.kind}</span><span className="evidence-summary">{item.summary}</span></summary><pre className="evidence-details">{item.id}{"\n"}{item.source}{"\n\n"}{JSON.stringify(item.details, null, 2)}</pre></details>)}</div>;
}

