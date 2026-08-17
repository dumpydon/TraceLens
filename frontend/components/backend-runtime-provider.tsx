"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import {
  BackendRuntimeMonitor,
  type BackendRuntimeStatus,
  isLocalApiBase,
} from "../lib/backend-runtime";

interface BackendRuntimeContextValue {
  status: BackendRuntimeStatus;
  isLocal: boolean;
  showReadyNotice: boolean;
  retry: () => void;
}

const BackendRuntimeContext = createContext<BackendRuntimeContextValue | null>(null);

export function BackendRuntimeProvider({ children }: { children: React.ReactNode }) {
  const monitorRef = useRef<BackendRuntimeMonitor | null>(null);
  if (monitorRef.current === null) monitorRef.current = new BackendRuntimeMonitor();

  const [status, setStatus] = useState<BackendRuntimeStatus>("checking");
  const [showReadyNotice, setShowReadyNotice] = useState(false);
  const previousStatus = useRef<BackendRuntimeStatus>("checking");

  useEffect(() => {
    const monitor = monitorRef.current!;
    const unsubscribe = monitor.subscribe((snapshot) => {
      const wasUnavailable = ["waking", "long_wait"].includes(previousStatus.current);
      previousStatus.current = snapshot.status;
      setStatus(snapshot.status);
      if (snapshot.status === "ready" && wasUnavailable) setShowReadyNotice(true);
    });
    monitor.start();
    return () => {
      unsubscribe();
      monitor.stop();
    };
  }, []);

  useEffect(() => {
    if (!showReadyNotice) return;
    const timer = window.setTimeout(() => setShowReadyNotice(false), 1_500);
    return () => window.clearTimeout(timer);
  }, [showReadyNotice]);

  return (
    <BackendRuntimeContext.Provider
      value={{
        status,
        isLocal: isLocalApiBase(),
        showReadyNotice,
        retry: () => monitorRef.current?.retry(),
      }}
    >
      {children}
    </BackendRuntimeContext.Provider>
  );
}

export function useBackendRuntime(): BackendRuntimeContextValue {
  const context = useContext(BackendRuntimeContext);
  if (!context) throw new Error("useBackendRuntime must be used inside BackendRuntimeProvider");
  return context;
}
