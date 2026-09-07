"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { Kbd } from "@/components/design/Primitives";
import { NAV, NAV_BOTTOM, type NavItem } from "@/components/shell/nav";
import { RP_DATA } from "@/lib/mockData";

function useUpdatesUnreadCount(enabled: boolean) {
  return useQuery<{ unread_count: number }>({
    queryKey: ["circulars", "updates-badge"],
    queryFn: async () => {
      const { data } = await api.get("/circulars/updates", {
        params: { page: 1, page_size: 1 },
      });
      return { unread_count: data.unread_count ?? 0 };
    },
    staleTime: 60_000,
    enabled,
  });
}

function useActionsOpenCount(enabled: boolean) {
  return useQuery<{ open: number }>({
    queryKey: ["action-items", "open-count"],
    queryFn: async () => {
      const { data } = await api.get("/action-items/stats");
      return { open: (data?.total ?? 0) - (data?.done ?? 0) };
    },
    staleTime: 60_000,
    enabled,
  });
}

function SidebarGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: "8px 0" }}>
      <div
        className="mono"
        style={{
          fontSize: 9.5,
          color: "var(--ink-4)",
          letterSpacing: ".12em",
          padding: "4px 16px 8px",
        }}
      >
        {label.toUpperCase()}
      </div>
      {children}
    </div>
  );
}

function NavRow({
  item,
  active,
  badge,
}: {
  item: NavItem;
  active: boolean;
  badge?: number;
}) {
  const Ic = item.icon;
  return (
    <Link
      href={item.href}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "7px 16px",
        cursor: "pointer",
        color: active ? "var(--ink)" : "var(--ink-3)",
        background: active ? "var(--panel-2)" : "transparent",
        borderLeft: `2px solid ${active ? "var(--signal)" : "transparent"}`,
        fontSize: 12.5,
        fontWeight: active ? 600 : 400,
        transition: "background .12s",
        textDecoration: "none",
      }}
    >
      <Ic style={{ opacity: active ? 1 : 0.7 }} />
      <span style={{ flex: 1 }}>{item.label}</span>
      {item.kbd ? <Kbd>{item.kbd}</Kbd> : null}
      {badge && badge > 0 ? (
        <span
          className="mono"
          style={{
            fontSize: 10,
            fontWeight: 600,
            background: item.signal ? "var(--signal)" : "var(--bg-2)",
            color: item.signal ? "#fff" : "var(--ink-3)",
            padding: "1px 5px",
            borderRadius: 2,
            minWidth: 18,
            textAlign: "center",
          }}
        >
          {badge}
        </span>
      ) : null}
      {item.signal && (!badge || badge <= 0) ? (
        <span className="live-dot" style={{ width: 6, height: 6 }} />
      ) : null}
      {item.tag ? (
        <span
          className="mono"
          style={{
            fontSize: 9,
            padding: "1px 4px",
            background: "var(--bg-2)",
            color: "var(--ink-4)",
            letterSpacing: ".1em",
            borderRadius: 2,
          }}
        >
          {item.tag}
        </span>
      ) : null}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const { data: updates } = useUpdatesUnreadCount(!!user);
  const { data: actions } = useActionsOpenCount(!!user);

  // Debate badge is not backed by a live endpoint yet; surface mock count.
  const badges: Record<string, number | undefined> = {
    updates: updates?.unread_count,
    actions: actions?.open,
    debate: 2,
  };

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/" || pathname.startsWith("/dashboard");
    return pathname.startsWith(href);
  };

  // Hide admin row unless user is_admin.
  const bottom = NAV_BOTTOM.filter(
    (item) => item.id !== "admin" || (user && user.is_admin),
  );

  return (
    <aside
      style={{
        width: 220,
        flexShrink: 0,
        background: "var(--panel)",
        borderRight: "1px solid var(--line)",
        display: "flex",
        flexDirection: "column",
        padding: "12px 0",
        overflowY: "auto",
      }}
    >
      <SidebarGroup label="Workspace">
        {NAV.map((item) => (
          <NavRow
            key={item.id}
            item={item}
            active={isActive(item.href)}
            badge={item.badgeKey ? badges[item.badgeKey] : undefined}
          />
        ))}
      </SidebarGroup>

      <div style={{ flex: 1 }} />

      <SidebarGroup label="Account">
        {bottom.map((item) => (
          <NavRow key={item.id} item={item} active={isActive(item.href)} />
        ))}
      </SidebarGroup>

      <div style={{ padding: "14px 16px 10px", borderTop: "1px solid var(--line)" }}>
        <div
          className="mono"
          style={{
            fontSize: 9.5,
            color: "var(--ink-4)",
            letterSpacing: ".12em",
            marginBottom: 8,
          }}
        >
          <span className="live-dot" style={{ marginRight: 6, verticalAlign: "middle" }} />
          LIVE · INDEX ACTIVE
        </div>
        <div style={{ fontSize: 11, color: "var(--ink-3)", lineHeight: 1.5 }}>
          Crawler indexed{" "}
          <b style={{ color: "var(--ink)" }}>{RP_DATA.pulse.thisWeek}</b> new circulars this week.
          Last scan: <b style={{ color: "var(--ink)" }}>2m ago</b>.
        </div>
      </div>
    </aside>
  );
}
