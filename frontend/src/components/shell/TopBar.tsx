"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Avatar, Btn, Icon, Kbd } from "@/components/design/Primitives";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";
import { RP_DATA } from "@/lib/mockData";

function LiveStat({
  label,
  value,
  trend,
  delta,
}: {
  label: string;
  value: string;
  trend?: "up" | "down" | "flat";
  delta?: string;
}) {
  const color = trend === "up" ? "var(--good)" : trend === "down" ? "var(--bad)" : "var(--ink-3)";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <span
        className="mono"
        style={{ fontSize: 9.5, color: "var(--ink-4)", letterSpacing: ".08em" }}
      >
        {label}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
        <span className="mono tnum" style={{ fontWeight: 600, fontSize: 12 }}>
          {value}
        </span>
        {delta ? (
          <span className="mono tnum" style={{ fontSize: 10, color }}>
            {delta}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function TopBar() {
  const router = useRouter();
  const theme = useThemeStore((s) => s.theme);
  const toggle = useThemeStore((s) => s.toggle);
  const user = useAuthStore((s) => s.user);

  // Prefer live user; fall back to mock for shell fidelity in demo.
  const displayName = user?.full_name ?? RP_DATA.user.name;
  const displayInitials =
    (user?.full_name?.split(" ") ?? [RP_DATA.user.name])
      .map((p) => p.trim()[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase() || RP_DATA.user.initials;
  const displayOrg = user?.org_name ?? RP_DATA.user.org;
  const credits = user?.credit_balance ?? RP_DATA.user.credits;

  const m = RP_DATA.market;

  // Keep the updates-unread badge live when authed, but we only surface it
  // in the sidebar — this query gives the topbar a sense of "liveness".
  useQuery({
    queryKey: ["topbar", "liveness"],
    queryFn: async () => ({ at: new Date().toISOString() }),
    staleTime: 60_000,
    enabled: false,
  });

  return (
    <div
      style={{
        height: 52,
        flexShrink: 0,
        background: "var(--panel)",
        borderBottom: "1px solid var(--line)",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        gap: 16,
      }}
    >
      <Link
        href="/dashboard"
        style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}
      >
        <div
          style={{
            width: 26,
            height: 26,
            background: "var(--ink)",
            color: "var(--bg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "var(--font-mono)",
            fontWeight: 700,
            fontSize: 13,
            borderRadius: 3,
            position: "relative",
          }}
        >
          <span>R</span>
          <span
            className="live-dot"
            style={{ position: "absolute", top: -2, right: -2, width: 6, height: 6 }}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
          <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: "-0.01em" }}>
            RegPulse
          </span>
          <span
            className="mono"
            style={{ fontSize: 9.5, color: "var(--ink-4)", letterSpacing: ".1em", marginTop: 2 }}
          >
            TERMINAL · v2.0
          </span>
        </div>
      </Link>

      <div style={{ width: 1, height: 24, background: "var(--line)" }} />

      <div style={{ display: "flex", gap: 18, alignItems: "center", fontSize: 11 }}>
        <LiveStat label="REPO" value={m.rbiRate.repo.toFixed(2) + "%"} trend="flat" />
        <LiveStat label="CRR" value={m.rbiRate.crr.toFixed(2) + "%"} trend="flat" />
        <LiveStat label="SLR" value={m.rbiRate.slr.toFixed(2) + "%"} trend="flat" />
        <LiveStat label="USD/INR" value={m.usdInr.toFixed(2)} trend="up" delta="+0.14" />
      </div>

      <div style={{ flex: 1 }} />

      <div
        onClick={() => window.dispatchEvent(new CustomEvent("rp:cmd"))}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          height: 30,
          padding: "0 10px",
          minWidth: 300,
          border: "1px solid var(--line)",
          borderRadius: 3,
          background: "var(--bg-1)",
          color: "var(--ink-3)",
          cursor: "pointer",
          fontSize: 12,
        }}
      >
        <Icon.Search style={{ opacity: 0.6 }} />
        <span>Ask anything, or jump to a circular…</span>
        <span style={{ flex: 1 }} />
        <Kbd>⌘K</Kbd>
      </div>

      <div
        onClick={() => router.push("/upgrade")}
        style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}
      >
        <span className="mono up" style={{ color: "var(--ink-4)", fontSize: 10 }}>
          CREDITS
        </span>
        <span className="mono tnum" style={{ fontWeight: 600 }}>
          {credits}
        </span>
        <div style={{ width: 48 }}>
          <div className="bar amber">
            <span style={{ width: `${Math.min(100, (credits / 300) * 100)}%` }} />
          </div>
        </div>
      </div>

      <Btn variant="ghost" icon onClick={toggle} title="Toggle theme">
        {theme === "dark" ? <Icon.Sun /> : <Icon.Moon />}
      </Btn>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Avatar initials={displayInitials} size={28} tone="signal" />
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
          <span style={{ fontSize: 12, fontWeight: 500 }}>{displayName}</span>
          <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>
            {displayOrg?.toUpperCase()}
          </span>
        </div>
      </div>
    </div>
  );
}
