"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Activity, ArrowRight, Beaker, ChartNoAxesCombined, ChevronsLeft, CircleGauge, Info, ListTree } from "lucide-react";
import { shouldShowRuntimeBriefing } from "@/lib/backend-runtime";
import { BackendStartupPanel } from "@/components/backend-startup-panel";
import { useBackendRuntime } from "@/components/backend-runtime-provider";
import { SystemBriefing } from "@/components/system-briefing";

const navigation = [
  { href: "/", label: "Overview", icon: CircleGauge },
  { href: "/incidents", label: "Incidents", icon: ListTree },
  { href: "/lab", label: "Incident Lab", icon: Beaker },
  { href: "/evaluations", label: "Evaluations", icon: ChartNoAxesCombined },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const runtime = useBackendRuntime();
  const current = navigation.find((item) => item.href === "/" ? pathname === "/" : pathname.startsWith(item.href));
  const currentLabel = pathname === "/about" ? "System Briefing" : current?.label ?? "Incident";
  const showBriefing = shouldShowRuntimeBriefing(runtime.status, pathname);
  const showStartupPanel = runtime.status !== "ready" || runtime.showReadyNotice;
  const runtimeLabel = runtime.status === "ready"
    ? "Investigation runtime connected"
    : runtime.status === "long_wait"
      ? "Investigation runtime unavailable"
      : runtime.status === "checking"
        ? "Checking investigation runtime"
      : "Investigation runtime initializing";
  const handleBriefingBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
      return;
    }
    router.push("/");
  };
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
        <div className={`sidebar-foot runtime-${runtime.status}`}>
          <i className="status-dot" />
          <span>{runtime.isLocal ? "Local environment" : "Hosted demo"}</span>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            <div className="breadcrumb">TraceLens / {currentLabel}</div>
            {pathname !== "/about" && (
              <Link className="briefing-entry" href="/about">
                <Info className="briefing-entry-info" size={15} />
                <span className="briefing-entry-label briefing-entry-label-full">How TraceLens works</span>
                <span className="briefing-entry-label briefing-entry-label-compact">How it works</span>
                <ArrowRight className="briefing-entry-arrow" size={13} />
              </Link>
            )}
          </div>
          <div className="env-chip mono">{runtime.isLocal ? "DEV" : "DEMO"}</div>
        </header>
        {pathname === "/about" && (
          <div className="about-back-row">
            <button type="button" className="briefing-back" onClick={handleBriefingBack}>
              <ChevronsLeft size={20} aria-hidden="true" />
              <span>Back</span>
            </button>
          </div>
        )}
        <div className={`content${pathname === "/" && !showBriefing ? " overview-content" : ""}`}>
          {showStartupPanel && (
            <BackendStartupPanel
              status={runtime.status}
              isLocal={runtime.isLocal}
            />
          )}
          {showBriefing ? <SystemBriefing /> : children}
        </div>
        <footer className="workspace-footer">
          <span className={`workspace-status mono runtime-${runtime.status}`}>
            <i className="workspace-status-dot" />
            <span className="workspace-status-copy">
              <span>{runtimeLabel}</span>
              {runtime.status === "ready" && <small>Render&apos;s Backend API</small>}
            </span>
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
