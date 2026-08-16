import Link from "next/link";
import type { Incident } from "@/lib/types";
import { formatRelativeTime } from "@/lib/format";
import { StatusBadge } from "./status-badge";

export function IncidentTable({ incidents }: { incidents: Incident[] }) {
  if (!incidents.length) return <div className="empty"><div><strong>No incidents recorded</strong>Generate traffic in the Incident Lab, then create an incident.</div></div>;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>ID</th><th>Incident</th><th>Service</th><th>Severity</th><th>Status</th><th>Started</th></tr></thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id}>
              <td className="mono"><Link href={`/incidents/${incident.id}`}>{incident.id}</Link></td>
              <td className="primary-cell"><Link href={`/incidents/${incident.id}`}>{incident.title}</Link></td>
              <td>{incident.service}</td><td><StatusBadge value={incident.severity} /></td>
              <td><StatusBadge value={incident.status} /></td><td>{formatRelativeTime(incident.started_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

