"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Beaker, ChartNoAxesCombined, CircleGauge, ListTree } from "lucide-react";

const navigation = [
  { href: "/", label: "Overview", icon: CircleGauge },
  { href: "/incidents", label: "Incidents", icon: ListTree },
  { href: "/lab", label: "Incident Lab", icon: Beaker },
  { href: "/evaluations", label: "Evaluations", icon: ChartNoAxesCombined },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const current = navigation.find((item) => item.href === "/" ? pathname === "/" : pathname.startsWith(item.href));
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <Link className="brand" href="/">
          <span className="brand-mark"><Activity size={14} /></span>
          <span>TraceLens</span>
        </Link>
        <div className="nav-label">Workspace</div>
        <nav>
          {navigation.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link key={href} className={`nav-link ${active ? "active" : ""}`} href={href} aria-current={active ? "page" : undefined}>
                <Icon size={16} strokeWidth={1.8} /> <span>{label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-foot"><i className="status-dot" /><span>Local environment</span></div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">TraceLens / {current?.label ?? "Incident"}</div>
          <div className="env-chip mono">DEV</div>
        </header>
        <div className="content">{children}</div>
        <footer className="workspace-footer">
          <span className="workspace-status mono">
            <i className="workspace-status-dot" />
            All systems operational
          </span>
          <nav className="workspace-footer-links" aria-label="Legal">
            <button type="button">Privacy policy</button>
            <button type="button">Terms of service</button>
          </nav>
        </footer>
      </main>
    </div>
  );
}
