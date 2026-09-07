"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon, Kbd } from "@/components/design/Primitives";
import { NAV } from "@/components/shell/nav";

interface PaletteItem {
  id: string;
  label: string;
  icon: (typeof Icon)[keyof typeof Icon];
  group: string;
  href: string;
}

const EXTRA: PaletteItem[] = [
  { id: "ask-sbr",  label: "Ask: Tier-1 impact of SBR revision",     icon: Icon.Ask,  group: "Recent asks",  href: "/ask" },
  { id: "ask-psl",  label: "Ask: PSL climate-adaptive sub-target",   icon: Icon.Ask,  group: "Recent asks",  href: "/ask" },
  { id: "circ-sbr", label: "DOR.CAP.REC.22 · SBR Revision",           icon: Icon.Book, group: "Circulars",    href: "/library" },
  { id: "circ-kyc", label: "DOR.AML.REC.18 · KYC Amendment",          icon: Icon.Book, group: "Circulars",    href: "/library" },
];

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!open) setQ("");
  }, [open]);

  if (!open) return null;

  const navItems: PaletteItem[] = NAV.map((n) => ({
    id: n.id,
    label: n.label,
    icon: n.icon,
    group: "Navigate",
    href: n.href,
  }));

  const items = [...navItems, ...EXTRA];
  const filtered = items.filter(
    (i) => q === "" || i.label.toLowerCase().includes(q.toLowerCase()),
  );
  const groups = filtered.reduce<Record<string, PaletteItem[]>>((acc, it) => {
    (acc[it.group] = acc[it.group] || []).push(it);
    return acc;
  }, {});

  const go = (href: string) => {
    router.push(href);
    onClose();
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 200,
        background: "rgba(0,0,0,.35)",
        display: "flex",
        justifyContent: "center",
        paddingTop: 120,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 560,
          height: "fit-content",
          background: "var(--panel)",
          border: "1px solid var(--line-2)",
          borderRadius: 4,
          boxShadow: "var(--shadow-lg)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: 12,
            borderBottom: "1px solid var(--line)",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <Icon.Search style={{ color: "var(--ink-3)" }} />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ask, search, or jump…"
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              fontSize: 14,
            }}
          />
          <Kbd>ESC</Kbd>
        </div>
        <div style={{ maxHeight: 400, overflowY: "auto", padding: "6px 0" }}>
          {Object.entries(groups).map(([g, list]) => (
            <div key={g}>
              <div
                className="mono up"
                style={{ fontSize: 9.5, color: "var(--ink-4)", padding: "8px 14px 4px" }}
              >
                {g}
              </div>
              {list.map((it) => {
                const Ic = it.icon;
                return (
                  <div
                    key={it.id}
                    onClick={() => go(it.href)}
                    style={{
                      padding: "8px 14px",
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                    }}
                    onMouseOver={(e) => (e.currentTarget.style.background = "var(--panel-2)")}
                    onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <Ic style={{ color: "var(--ink-4)" }} />
                    {it.label}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
