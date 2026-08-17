import Link from "next/link";
import type { Incident } from "@/lib/types";
import { formatRelativeTime } from "@/lib/format";
import { StatusBadge } from "./status-badge";

export function IncidentTable({ incidents, startedColumnPosition = "last" }: { incidents: Incident[]; startedColumnPosition?: "third" | "last" }) {
  if (!incidents.length) return <div className="empty"><div><strong>No incidents recorded</strong>Generate traffic in the Incident Lab, then create an incident.</div></div>;
  const startedThird = startedColumnPosition === "third";
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>ID</th><th>Incident</th>{startedThird && <th>Started</th>}<th>Service</th><th>Severity</th><th>Status</th>{!startedThird && <th>Started</th>}</tr></thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id}>
              <td className="mono"><Link href={`/incidents/${incident.id}`}>{incident.id}</Link></td>
              <td className="primary-cell"><Link href={`/incidents/${incident.id}`}>{incident.title}</Link></td>
              {startedThird && <td>{formatRelativeTime(incident.started_at)}</td>}
              <td>{incident.service}</td><td><StatusBadge value={incident.severity} /></td>
              <td><StatusBadge value={incident.status} /></td>{!startedThird && <td>{formatRelativeTime(incident.started_at)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
