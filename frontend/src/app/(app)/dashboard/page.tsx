"use client";

import Link from "next/link";
import { useState, Fragment } from "react";
import { useRouter } from "next/navigation";
import {
  Btn,
  Icon,
  Kbd,
  Pill,
  Sparkline,
} from "@/components/design/Primitives";
import { useAuthStore } from "@/stores/authStore";
import { RP_DATA, type ActionMock } from "@/lib/mockData";
import { useDashboardPulse } from "@/hooks/useDashboard";
import { useDebates } from "@/hooks/useDebates";

// <Link> rendering a <button> child is invalid HTML, so we use a router push
// inside Btn's onClick. Keeps a11y (real <button>) and the ghost/sm styling.
function LinkBtn({
  href,
  children,
  ...rest
}: {
  href: string;
  children: React.ReactNode;
  variant?: "" | "primary" | "accent" | "ghost";
  size?: "" | "sm";
}) {
  const router = useRouter();
  return (
    <Btn {...rest} onClick={() => router.push(href)}>
      {children}
    </Btn>
  );
}

export default function DashboardPage() {
  const { data: pulseData } = useDashboardPulse();
  const pulse = pulseData?.pulse;

  const totalCirculars = pulse?.total_circulars ?? RP_DATA.pulse.totalCirculars;
  const questionsAsked = pulse?.questions_asked ?? RP_DATA.pulse.questionsAsked;
  const learningsCaptured = pulse?.learnings_captured ?? RP_DATA.pulse.learningsCaptured;
  const sparkline = pulse?.sparkline ?? RP_DATA.pulse.sparkline;

  return (
    <div
      style={{
        padding: "20px 24px 40px",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <DashHero />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          gap: 12,
        }}
      >
        <MetricTile
          label="CIRCULARS INDEXED"
          value={totalCirculars.toLocaleString()}
          delta="+7 wk"
          trend="up"
          sparkline={sparkline}
        />
        <MetricTile
          label="QUESTIONS ASKED"
          value={questionsAsked.toLocaleString()}
          delta="+142 wk"
          trend="up"
          sparkline={[10, 12, 14, 18, 16, 22, 20, 24, 19, 23, 25, 27, 24, 29]}
        />
        <MetricTile
          label="TEAM LEARNINGS"
          value={String(learningsCaptured)}
          delta="+14 wk"
          trend="up"
          sparkline={[1, 2, 1, 3, 2, 4, 3, 5, 4, 6, 5, 7, 6, 8]}
          signal
        />
        <MetricTile
          label="AVG CONFIDENCE"
          value="0.81"
          delta="+0.03"
          trend="up"
          sparkline={[0.72, 0.74, 0.78, 0.77, 0.8, 0.79, 0.83, 0.82, 0.84, 0.81, 0.82, 0.85, 0.83, 0.86]}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.35fr 1fr", gap: 16 }}>
        <ThisWeekBrief />
        <HeatmapPanel />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 16 }}>
        <ActivityStream />
        <ExposurePanel />
      </div>

      <OpenDebates />
    </div>
  );
}

/* ---------------------------------- Hero ---------------------------------- */
function DashHero() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const firstName = (user?.full_name ?? RP_DATA.user.name).split(" ")[0];
  const [q, setQ] = useState("");
  const placeholder =
    "What does the April 20 SBR revision mean for our Tier-1 planning?";

  const goAsk = () => {
    const url = q.trim() ? `/ask?q=${encodeURIComponent(q.trim())}` : "/ask";
    router.push(url);
  };

  return (
    <div
      className="panel"
      style={{
        padding: "22px 24px",
        position: "relative",
        overflow: "hidden",
        display: "grid",
        gridTemplateColumns: "1.2fr 1fr",
        gap: 24,
        borderColor: "var(--line-2)",
      }}
    >
      <div
        className="gridlines"
        style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.35 }}
      />

      <div style={{ position: "relative" }}>
        <div
          style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}
        >
          <span className="mono up" style={{ fontSize: 10, color: "var(--ink-4)" }}>
            {RP_DATA.market.asOf}
          </span>
          <span style={{ width: 1, height: 10, background: "var(--line-2)" }} />
          <span
            className="mono"
            style={{
              fontSize: 10,
              color: "var(--signal)",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
          >
            <span className="live-dot" style={{ width: 6, height: 6 }} />
            LIVE
          </span>
        </div>
        <h1
          className="serif"
          style={{
            fontSize: 30,
            fontWeight: 400,
            lineHeight: 1.15,
            letterSpacing: "-0.015em",
            marginBottom: 6,
            color: "var(--ink)",
          }}
        >
          Good morning, {firstName}.
        </h1>
        <p
          className="serif"
          style={{
            fontSize: 17,
            lineHeight: 1.5,
            color: "var(--ink-2)",
            fontStyle: "italic",
            maxWidth: 540,
          }}
        >
          Three circulars hit your desk this week. One{" "}
          <b style={{ color: "var(--signal)", fontStyle: "normal" }}>
            materially affects FY27 capital planning
          </b>{" "}
          — the rest can wait until after the board.
        </p>

        <div style={{ marginTop: 18, display: "flex", gap: 8 }}>
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              gap: 10,
              border: "1px solid var(--line-2)",
              background: "var(--bg)",
              padding: "10px 14px",
              borderRadius: 3,
            }}
          >
            <Icon.Ask style={{ color: "var(--signal)" }} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && goAsk()}
              placeholder={placeholder}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                fontSize: 14,
              }}
            />
            <Kbd>↵</Kbd>
          </div>
          <Btn variant="accent" onClick={goAsk}>
            Ask <Icon.Arrow />
          </Btn>
        </div>

        <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
          {[
            "Tier-1 impact of SBR revision",
            "PSL climate-adaptive sub-target",
            "ECB — SOFR linkage deadline",
            "Video-KYC liveness for re-KYC",
          ].map((s) => (
            <Link
              key={s}
              href={`/ask?q=${encodeURIComponent(s)}`}
              style={{
                fontSize: 11,
                padding: "4px 9px",
                border: "1px solid var(--line)",
                background: "var(--panel-2)",
                color: "var(--ink-3)",
                borderRadius: 20,
                cursor: "pointer",
                fontFamily: "var(--font-mono)",
                letterSpacing: ".02em",
                textDecoration: "none",
              }}
            >
              {s}
            </Link>
          ))}
        </div>
      </div>

      <div
        style={{
          position: "relative",
          borderLeft: "1px solid var(--line-2)",
          paddingLeft: 24,
        }}
      >
        <div className="tick" style={{ marginBottom: 12 }}>
          TOP OF MIND · CURATED
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <TopCard
            tag="MATERIAL"
            tone="amber"
            title="SBR Revision — Tier-1 floor 10%, leverage cap 7×"
            sub="2 actions, 3 teams · 14 pages · 6-min read"
            href="/ask"
          />
          <TopCard
            tag="DEADLINE"
            tone="warn"
            title="PSL shortfall filing due in 9 days"
            sub="Q4 FY26 · Reporting team · self-filing portal"
            href="/action-items"
          />
          <TopCard
            tag="DEBATE"
            tone="blue"
            title="Leverage cap — does securitised pool count?"
            sub="2 replies from Risk and Treasury · unresolved"
            href="/debate"
          />
        </div>
      </div>
    </div>
  );
}

function TopCard({
  tag,
  tone,
  title,
  sub,
  href,
}: {
  tag: string;
  tone: "amber" | "warn" | "blue";
  title: string;
  sub: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      style={{
        padding: "10px 12px",
        borderRadius: 3,
        cursor: "pointer",
        border: "1px solid var(--line)",
        background: "var(--bg)",
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        transition: "border-color .15s, background .15s",
        textDecoration: "none",
        color: "inherit",
      }}
      onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--ink-4)")}
      onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--line)")}
    >
      <Pill tone={tone} style={{ marginTop: 1 }}>
        {tag}
      </Pill>
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontSize: 13,
            fontWeight: 500,
            marginBottom: 2,
            lineHeight: 1.3,
          }}
        >
          {title}
        </div>
        <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>
          {sub}
        </div>
      </div>
      <Icon.Arrow style={{ color: "var(--ink-4)", marginTop: 2 }} />
    </Link>
  );
}

/* ------------------------------- Metric tile ------------------------------ */
function MetricTile({
  label,
  value,
  delta,
  trend = "up",
  sparkline,
  signal = false,
}: {
  label: string;
  value: string;
  delta?: string;
  trend?: "up" | "down";
  sparkline?: number[];
  signal?: boolean;
}) {
  const color = trend === "up" ? "var(--good)" : "var(--bad)";
  return (
    <div className="panel" style={{ padding: 14, position: "relative", overflow: "hidden" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <span
          className="mono"
          style={{ fontSize: 10, color: "var(--ink-4)", letterSpacing: ".08em" }}
        >
          {label}
        </span>
        {signal ? <span className="live-dot" style={{ width: 6, height: 6 }} /> : null}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 10,
        }}
      >
        <div>
          <div
            className="tnum"
            style={{
              fontSize: 24,
              fontWeight: 600,
              lineHeight: 1,
              letterSpacing: "-0.02em",
            }}
          >
            {value}
          </div>
          {delta ? (
            <div
              className="mono tnum"
              style={{
                fontSize: 10.5,
                color,
                marginTop: 4,
                display: "flex",
                alignItems: "center",
                gap: 3,
              }}
            >
              {trend === "up" ? <Icon.Up /> : <Icon.Down />} {delta}
            </div>
          ) : null}
        </div>
        {sparkline ? <Sparkline data={sparkline} width={80} height={28} /> : null}
      </div>
    </div>
  );
}

/* ------------------------------- This Week -------------------------------- */
function ThisWeekBrief() {
  const circs = RP_DATA.circulars.filter((c) => c.daysAgo <= 9 && c.status === "active");
  return (
    <div className="panel">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "12px 16px",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div className="tick">THIS WEEK · WHAT MOVED</div>
        <div style={{ flex: 1 }} />
        <LinkBtn href="/updates" variant="ghost" size="sm">
          All updates <Icon.Arrow />
        </LinkBtn>
      </div>
      <div>
        {circs.map((c, i) => (
          <Link
            key={c.id}
            href="/library"
            style={{
              display: "grid",
              gridTemplateColumns: "44px 80px 1fr auto",
              gap: 12,
              padding: "14px 16px",
              borderBottom: i === circs.length - 1 ? "none" : "1px solid var(--line)",
              cursor: "pointer",
              transition: "background .12s",
              alignItems: "start",
              textDecoration: "none",
              color: "inherit",
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "var(--panel-2)")}
            onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}
          >
            <div style={{ textAlign: "center" }}>
              <div
                className="mono tnum"
                style={{ fontSize: 18, fontWeight: 600, lineHeight: 1 }}
              >
                {c.date.split(" ")[0]}
              </div>
              <div
                className="mono up"
                style={{ fontSize: 9, color: "var(--ink-4)", marginTop: 2 }}
              >
                {c.date.split(" ")[1]}
              </div>
            </div>

            <div>
              <Pill
                tone={c.impact === "high" ? "amber" : c.impact === "med" ? "warn" : "ghost"}
              >
                {c.impact.toUpperCase()}
              </Pill>
            </div>

            <div>
              <div
                className="mono"
                style={{ fontSize: 10.5, color: "var(--ink-4)", marginBottom: 3 }}
              >
                {c.num}
              </div>
              <div
                style={{
                  fontSize: 13.5,
                  fontWeight: 500,
                  lineHeight: 1.35,
                  marginBottom: 5,
                  color: "var(--ink)",
                }}
              >
                {c.title}
              </div>
              {c.summary ? (
                <div
                  className="serif"
                  style={{
                    fontSize: 13,
                    color: "var(--ink-2)",
                    fontStyle: "italic",
                    marginBottom: 6,
                    lineHeight: 1.45,
                  }}
                >
                  {c.summary}
                </div>
              ) : null}
              <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                {c.tags.map((t) => (
                  <Pill key={t} tone="ghost">
                    {t}
                  </Pill>
                ))}
                {c.deadline ? <Pill tone="warn">Due {c.deadline}</Pill> : null}
              </div>
            </div>

            <Icon.Arrow style={{ color: "var(--ink-4)", marginTop: 4 }} />
          </Link>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------- Heatmap --------------------------------- */
function HeatmapPanel() {
  const { data } = useDashboardPulse();
  const h = data?.heatmap?.rows?.length ? data.heatmap : RP_DATA.heatmap;
  const max = Math.max(...h.rows.flatMap((r) => r.vals));

  const color = (v: number) => {
    if (v === 0) return "var(--bg-2)";
    const t = v / max;
    return `color-mix(in oklab, var(--signal) ${Math.round(t * 85 + 10)}%, var(--bg-2))`;
  };

  return (
    <div className="panel" style={{ padding: "14px 16px" }}>
      <div className="tick" style={{ marginBottom: 12 }}>
        QUESTIONS BY DOMAIN · LAST 7 DAYS
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "120px repeat(7, 1fr)",
          gap: 3,
          alignItems: "center",
        }}
      >
        <div />
        {h.cols.map((c) => (
          <div
            key={c}
            className="mono up"
            style={{ fontSize: 9.5, color: "var(--ink-4)", textAlign: "center" }}
          >
            {c}
          </div>
        ))}
        {h.rows.map((r) => (
          <Fragment key={r.name}>
            <div style={{ fontSize: 11.5, color: "var(--ink-2)" }}>{r.name}</div>
            {r.vals.map((v, i) => (
              <div
                key={i}
                title={`${v} questions`}
                style={{
                  height: 22,
                  background: color(v),
                  borderRadius: 1.5,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "var(--font-mono)",
                  fontSize: 10.5,
                  color: v / max > 0.5 ? "#fff" : "var(--ink-3)",
                  fontWeight: 500,
                  transition: "transform .12s",
                  cursor: "pointer",
                }}
                onMouseOver={(e) => (e.currentTarget.style.transform = "scale(1.15)")}
                onMouseOut={(e) => (e.currentTarget.style.transform = "scale(1)")}
              >
                {v || ""}
              </div>
            ))}
          </Fragment>
        ))}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginTop: 14,
          fontSize: 10.5,
          color: "var(--ink-4)",
        }}
        className="mono"
      >
        <span>LESS</span>
        {[0.1, 0.25, 0.5, 0.75, 1].map((t) => (
          <div
            key={t}
            style={{
              width: 14,
              height: 10,
              borderRadius: 1.5,
              background: `color-mix(in oklab, var(--signal) ${Math.round(
                t * 85 + 10,
              )}%, var(--bg-2))`,
            }}
          />
        ))}
        <span>MORE</span>
        <span style={{ flex: 1 }} />
        <span>62 QUESTIONS</span>
      </div>
    </div>
  );
}

/* -------------------------------- Activity -------------------------------- */
function ActivityStream() {
  const { data } = useDashboardPulse();
  const items = data?.activity?.length ? data.activity : RP_DATA.activity;
  const typeStyle: Record<string, { color: string; label: string }> = {
    circ:   { color: "var(--signal)",      label: "CIRC" },
    ask:    { color: "var(--accent-blue)", label: "ASK" },
    save:   { color: "var(--ink-3)",       label: "SAVE" },
    learn:  { color: "var(--good)",        label: "LEARN" },
    debate: { color: "var(--warn)",        label: "DBATE" },
  };
  return (
    <div className="panel">
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--line)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div className="tick">ACTIVITY · LIVE STREAM</div>
        <span className="live-dot" style={{ width: 6, height: 6 }} />
      </div>
      <div style={{ padding: "4px 0" }}>
        {items.map((a, i) => {
          const s = typeStyle[a.type];
          return (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: "44px 52px 1fr",
                gap: 10,
                padding: "8px 16px",
                fontSize: 12,
                borderBottom:
                  i === items.length - 1 ? "none" : "1px solid var(--line)",
                alignItems: "center",
              }}
            >
              <span
                className="mono tnum"
                style={{ fontSize: 11, color: "var(--ink-4)" }}
              >
                {a.when}
              </span>
              <span
                className="mono"
                style={{
                  fontSize: 9.5,
                  color: s.color,
                  fontWeight: 600,
                  letterSpacing: ".08em",
                }}
              >
                {s.label}
              </span>
              <span style={{ color: "var(--ink-2)" }}>{a.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* -------------------------------- Exposure -------------------------------- */
function ExposurePanel() {
  const items = RP_DATA.actionItems;
  const byTeam = items.reduce<
    Record<string, { total: number; done: number; high: number }>
  >((acc, it: ActionMock) => {
    acc[it.team] = acc[it.team] || { total: 0, done: 0, high: 0 };
    acc[it.team].total++;
    if (it.status === "done") acc[it.team].done++;
    if (it.priority === "high") acc[it.team].high++;
    return acc;
  }, {});
  const teams = Object.entries(byTeam).sort((a, b) => b[1].high - a[1].high);

  return (
    <div className="panel">
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--line)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div className="tick">EXPOSURE · BY TEAM</div>
        <div style={{ flex: 1 }} />
        <LinkBtn href="/action-items" variant="ghost" size="sm">
          Action items <Icon.Arrow />
        </LinkBtn>
      </div>
      <table className="dtable">
        <thead>
          <tr>
            <th>Team</th>
            <th style={{ width: 60, textAlign: "right" }}>Open</th>
            <th style={{ width: 70, textAlign: "right" }}>High</th>
            <th style={{ width: 120 }}>Progress</th>
          </tr>
        </thead>
        <tbody>
          {teams.map(([name, s]) => (
            <tr key={name}>
              <td style={{ fontWeight: 500 }}>{name}</td>
              <td className="mono tnum" style={{ textAlign: "right" }}>
                {s.total - s.done}
              </td>
              <td
                className="mono tnum"
                style={{
                  textAlign: "right",
                  color: s.high ? "var(--signal)" : "var(--ink-4)",
                  fontWeight: s.high ? 600 : 400,
                }}
              >
                {s.high || "—"}
              </td>
              <td>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div className="bar amber" style={{ flex: 1 }}>
                    <span style={{ width: `${(s.done / s.total) * 100}%` }} />
                  </div>
                  <span
                    className="mono"
                    style={{
                      fontSize: 10,
                      color: "var(--ink-4)",
                      minWidth: 30,
                      textAlign: "right",
                    }}
                  >
                    {Math.round((s.done / s.total) * 100)}%
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------- Open debates ----------------------------- */
function OpenDebates() {
  const { data: serverDebates } = useDebates();
  const debates = serverDebates && serverDebates.length > 0 ? serverDebates.slice(0, 2) : [
    {
      title: "Leverage cap — does de-recognised securitised pool count?",
      source_ref: "SBR Revision · DOR.CAP.REC.22",
      replies: [{ who: "AS", role: "Treasury" }],
      stance_agree: 2,
      stance_disagree: 2,
    },
    {
      title: "Video-KYC liveness — applies to routine re-KYC or only OVD refresh?",
      source_ref: "KYC Amendment · DOR.AML.REC.18",
      replies: [{ who: "VN", role: "Compliance" }],
      stance_agree: 1,
      stance_disagree: 3,
    }
  ];

  return (
    <div className="panel" style={{ padding: "14px 16px" }}>
      <div
        style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}
      >
        <div className="tick">OPEN DEBATES · YOUR TEAM IS DISAGREEING</div>
        <div style={{ flex: 1 }} />
        <LinkBtn href="/debate" variant="ghost" size="sm">
          All debates <Icon.Arrow />
        </LinkBtn>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {debates.map((d, i) => {
          const lastReply = d.replies && d.replies.length > 0 
            ? `${d.replies[d.replies.length-1].who}, ${d.replies[d.replies.length-1].role || 'Team'} — 1h ago` 
            : "No replies yet";
          return (
            <DebateCard
              key={i}
              title={d.title}
              src={d.source_ref || "SYSTEM"}
              lastReply={lastReply}
              stance={{ agree: d.stance_agree, disagree: d.stance_disagree }}
            />
          );
        })}
      </div>
    </div>
  );
}

function DebateCard({
  title,
  src,
  lastReply,
  stance,
}: {
  title: string;
  src: string;
  lastReply: string;
  stance: { agree: number; disagree: number };
}) {
  const total = stance.agree + stance.disagree;
  return (
    <Link
      href="/debate"
      style={{
        padding: 12,
        border: "1px solid var(--line)",
        borderRadius: 3,
        cursor: "pointer",
        background: "var(--bg)",
        transition: "border-color .15s",
        textDecoration: "none",
        color: "inherit",
        display: "block",
      }}
      onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--ink-4)")}
      onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--line)")}
    >
      <div
        style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.35, marginBottom: 6 }}
      >
        {title}
      </div>
      <div
        className="mono"
        style={{ fontSize: 10.5, color: "var(--ink-4)", marginBottom: 10 }}
      >
        {src}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            flex: 1,
            height: 4,
            borderRadius: 2,
            overflow: "hidden",
            background: "var(--line)",
            display: "flex",
          }}
        >
          <div
            style={{
              width: `${(stance.agree / total) * 100}%`,
              background: "var(--good)",
            }}
          />
          <div
            style={{
              width: `${(stance.disagree / total) * 100}%`,
              background: "var(--bad)",
            }}
          />
        </div>
        <span className="mono" style={{ fontSize: 10, color: "var(--good)" }}>
          {stance.agree} agree
        </span>
        <span className="mono" style={{ fontSize: 10, color: "var(--bad)" }}>
          {stance.disagree} disagree
        </span>
      </div>
      <div
        className="mono"
        style={{ fontSize: 10.5, color: "var(--ink-4)", marginTop: 8 }}
      >
        Last: {lastReply}
      </div>
    </Link>
  );
}
