import type { InvestigationEvent } from "@/lib/types";

export function EventTimeline({ events }: { events: InvestigationEvent[] }) {
  if (!events.length) return <div className="empty"><div><strong>Investigation not started</strong>Start the graph to see semantic progress events.</div></div>;
  return <div className="timeline" aria-live="polite">{events.map((event) => {
    const variant = event.event_type.includes("completed") ? "complete" : event.event_type.includes("failed") ? "failed" : "";
    return <div className={`event ${variant}`} key={event.id}><time className="event-time">{new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time><span className="event-marker" /><div><div className="event-title">{event.summary}</div><div className="event-stage">{event.stage} · {event.event_type.replaceAll("_", " ")}</div></div></div>;
  })}</div>;
}

