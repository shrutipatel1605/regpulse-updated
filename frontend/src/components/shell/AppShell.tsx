"use client";

import { useEffect, useState } from "react";
import { ToastProvider } from "@/components/design/Primitives";
import { TopBar } from "@/components/shell/TopBar";
import { Ticker } from "@/components/shell/Ticker";
import { Sidebar } from "@/components/shell/Sidebar";
import { CommandPalette } from "@/components/shell/CommandPalette";
import { TweaksPanel } from "@/components/shell/TweaksPanel";

/**
 * App shell — TopBar + Ticker + Sidebar + route content. Owns the ⌘K
 * palette and the Tweaks panel. Re-renders the content wrapper on
 * route change via the `key` prop so the fadeIn animation replays.
 */
export function AppShell({
  children,
  routeKey,
}: {
  children: React.ReactNode;
  routeKey: string;
}) {
  const [cmdOpen, setCmdOpen] = useState(false);
  const [tweaksOpen, setTweaksOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen((o) => !o);
      }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === "t") {
        e.preventDefault();
        setTweaksOpen((o) => !o);
      }
      if (e.key === "Escape") {
        setCmdOpen(false);
      }
    };
    const onCmd = () => setCmdOpen((o) => !o);
    window.addEventListener("keydown", onKey);
    window.addEventListener("rp:cmd", onCmd);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("rp:cmd", onCmd);
    };
  }, []);

  return (
    <ToastProvider>
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
        <TopBar />
        <Ticker />
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          <Sidebar />
          <main style={{ flex: 1, overflow: "hidden", background: "var(--bg)" }}>
            <div
              key={routeKey}
              className="rp-route-fade"
              style={{ height: "100%", overflow: "auto" }}
            >
              {children}
            </div>
          </main>
        </div>

        {/* Floating tweaks launcher (bottom-right, only when closed) */}
        {!tweaksOpen && (
          <button
            onClick={() => setTweaksOpen(true)}
            title="Tweaks (⌘⇧T)"
            aria-label="Open tweaks"
            style={{
              position: "fixed",
              right: 20,
              bottom: 20,
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "var(--panel)",
              border: "1px solid var(--line-2)",
              color: "var(--signal)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              boxShadow: "var(--shadow-lg)",
              zIndex: 40,
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
        )}

        <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
        <TweaksPanel open={tweaksOpen} onClose={() => setTweaksOpen(false)} />
      </div>
    </ToastProvider>
  );
}
