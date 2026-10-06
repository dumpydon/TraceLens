"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import {
  BackendRuntimeMonitor,
  type BackendRuntimeStatus,
  isLocalApiBase,
} from "../lib/backend-runtime";
import { activateWarmWindow } from "../lib/warm-window";

interface BackendRuntimeContextValue {
  status: BackendRuntimeStatus;
  isLocal: boolean;
  showReadyNotice: boolean;
  coldStartRecoveryId: number;
  retry: () => void;
}

const BackendRuntimeContext = createContext<BackendRuntimeContextValue | null>(null);

export function BackendRuntimeProvider({ children }: { children: React.ReactNode }) {
  const monitorRef = useRef<BackendRuntimeMonitor | null>(null);
  if (monitorRef.current === null) monitorRef.current = new BackendRuntimeMonitor();

  const [status, setStatus] = useState<BackendRuntimeStatus>("checking");
  const [showReadyNotice, setShowReadyNotice] = useState(false);
  const [coldStartRecoveryId, setColdStartRecoveryId] = useState(0);
  const previousStatus = useRef<BackendRuntimeStatus>("checking");
  const experiencedColdStart = useRef(false);
  const emittedColdStartRecovery = useRef(false);

  useEffect(() => {
    void activateWarmWindow(isLocalApiBase());
    const monitor = monitorRef.current!;
    const unsubscribe = monitor.subscribe((snapshot) => {
      const wasUnavailable = ["waking", "long_wait"].includes(previousStatus.current);
      previousStatus.current = snapshot.status;
      setStatus(snapshot.status);
      if (["waking", "long_wait"].includes(snapshot.status)) experiencedColdStart.current = true;
      if (snapshot.status === "ready" && (wasUnavailable || experiencedColdStart.current)) {
        experiencedColdStart.current = false;
        setShowReadyNotice(true);
        if (!emittedColdStartRecovery.current) {
          emittedColdStartRecovery.current = true;
          setColdStartRecoveryId((current) => current + 1);
        }
      }
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
        coldStartRecoveryId,
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
