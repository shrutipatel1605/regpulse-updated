"use client";

import { RP_DATA } from "@/lib/mockData";
import { Avatar, Btn, Icon, MiniStat, Pill } from "@/components/design/Primitives";
import { useLearnings } from "@/hooks/useLearnings";

export default function LearningsPage() {
  const { data: serverLearnings } = useLearnings();

  const mockItems = RP_DATA.learnings;
  
  // Format server learnings to match UI needs
  const liveItems = (serverLearnings || []).map(sl => ({
    id: sl.id,
    by: sl.user_initials || "U",
    when: new Date(sl.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    title: sl.title,
    note: sl.note,
    tags: sl.tags,
    src: sl.source_ref || "SYSTEM"
  }));

  // Fallback to mock if DB is empty
  const items = liveItems.length > 0 ? liveItems : mockItems;

  return (
    <div className="rp-route-fade" style={{ padding: "20px 24px 60px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 6,
        }}
      >
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 400 }}>
          Team Learnings
        </h1>
        <span className="live-dot" />
      </div>
      <p
        className="serif"
        style={{
          fontSize: 14,
          fontStyle: "italic",
          color: "var(--ink-3)",
          marginBottom: 20,
        }}
      >
        The institutional memory of your compliance team — one-line takeaways,
        pinned from briefs, shared with the team.
      </p>

      {/* Stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <MiniStat label="CAPTURED · TOTAL" value="96" />
        <MiniStat label="THIS WEEK" value="14" signal />
        <MiniStat label="CONTRIBUTORS" value="5" />
      </div>

      {/* Learning cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map((l) => (
          <div
            key={l.id}
            className="panel"
            style={{
              padding: 14,
              display: "grid",
              gridTemplateColumns: "60px 1fr auto",
              gap: 14,
              alignItems: "start",
            }}
          >
            {/* Avatar + when */}
            <div style={{ textAlign: "center" }}>
              <Avatar
                initials={l.by}
                size={32}
                tone={l.by === "PM" ? "signal" : "default"}
              />
              <div
                className="mono"
                style={{ fontSize: 9.5, color: "var(--ink-4)", marginTop: 4 }}
              >
                {l.when}
              </div>
            </div>

            {/* Content */}
            <div>
              <div
                className="serif"
                style={{
                  fontSize: 16,
                  lineHeight: 1.35,
                  color: "var(--ink)",
                  marginBottom: 6,
                }}
              >
                <Icon.Spark
                  style={{
                    color: "var(--signal)",
                    display: "inline",
                    marginRight: 6,
                    verticalAlign: "baseline",
                  }}
                />
                {l.title}
              </div>
              {l.note && (
                <div
                  className="serif"
                  style={{
                    fontSize: 13,
                    fontStyle: "italic",
                    color: "var(--ink-3)",
                    lineHeight: 1.5,
                    marginBottom: 8,
                  }}
                >
                  {l.note}
                </div>
              )}
              <div
                style={{
                  display: "flex",
                  gap: 5,
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                {l.tags.map((t) => (
                  <Pill key={t} tone="ghost">
                    #{t}
                  </Pill>
                ))}
                <span style={{ color: "var(--ink-4)" }}>·</span>
                <span
                  className="mono"
                  style={{ fontSize: 10.5, color: "var(--signal)" }}
                >
                  Source: {l.src.toUpperCase()}
                </span>
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <Btn size="sm" variant="ghost">
                <Icon.Pin /> Pin
              </Btn>
              <Btn size="sm" variant="ghost">
                Edit
              </Btn>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
