"use client";

import { RP_DATA, type TickerItem } from "@/lib/mockData";

export function Ticker() {
  const items = RP_DATA.market.ticker;
  const loop: TickerItem[] = [...items, ...items];
  return (
    <div
      style={{
        borderBottom: "1px solid var(--line)",
        background: "var(--panel)",
        overflow: "hidden",
        height: 28,
        position: "relative",
        flexShrink: 0,
      }}
    >
      <div className="ticker-track" style={{ padding: "6px 0" }}>
        {loop.map((t, i) => (
          <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 11.5 }}>
            <span
              className="mono"
              style={{
                fontSize: 10,
                padding: "1px 5px",
                borderRadius: 2,
                background:
                  t.impact === "high"
                    ? "var(--signal-bg)"
                    : t.impact === "med"
                      ? "var(--warn-bg)"
                      : "var(--bg-2)",
                color:
                  t.impact === "high"
                    ? "var(--signal-ink)"
                    : t.impact === "med"
                      ? "var(--warn)"
                      : "var(--ink-3)",
                letterSpacing: ".08em",
              }}
            >
              {t.tag}
            </span>
            <span style={{ color: "var(--ink-2)" }}>{t.text}</span>
            <span style={{ color: "var(--ink-5)" }}>•</span>
          </span>
        ))}
      </div>
    </div>
  );
}
