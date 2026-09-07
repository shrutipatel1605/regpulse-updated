"use client";

import { Btn, Icon, Pill } from "@/components/design/Primitives";
import { useDebates } from "@/hooks/useDebates";

const THREADS = [
  {
    title: "Leverage cap — does de-recognised securitised pool count?",
    src: "SBR Revision · DOR.CAP.REC.22",
    replies: 4,
    stance: { agree: 2, disagree: 2 },
    open: true,
  },
  {
    title: "Video-KYC liveness — applies to routine re-KYC or only OVD refresh?",
    src: "KYC Amendment · DOR.AML.REC.18",
    replies: 5,
    stance: { agree: 1, disagree: 3 },
    open: true,
  },
  {
    title: "PSL climate-adaptive — does cooperative lending qualify?",
    src: "PSL Targets · DOR.PSL.REC.07",
    replies: 3,
    stance: { agree: 3, disagree: 0 },
    open: false,
  },
  {
    title: "ECB fallback — retro-execution of SOFR amendment",
    src: "ECB · FED.FE.REC.09",
    replies: 2,
    stance: { agree: 2, disagree: 0 },
    open: false,
  },
];

export default function DebatePage() {
  const { data: serverDebates } = useDebates();
  
  const liveItems = (serverDebates || []).map(d => ({
    title: d.title,
    src: d.source_ref || "SYSTEM",
    replies: d.replies.length,
    stance: { agree: d.stance_agree, disagree: d.stance_disagree },
    open: d.status === "OPEN"
  }));
  
  const items = liveItems.length > 0 ? liveItems : THREADS;

  return (
    <div className="rp-route-fade" style={{ padding: "20px 24px 60px" }}>
      <h1
        className="serif"
        style={{ fontSize: 28, fontWeight: 400, marginBottom: 4 }}
      >
        Debates
      </h1>
      <p
        className="serif"
        style={{
          fontSize: 14,
          fontStyle: "italic",
          color: "var(--ink-3)",
          marginBottom: 20,
        }}
      >
        Where your team&rsquo;s disagreements become a record — annotate briefs,
        argue the interpretation, let the strongest reading win.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
        }}
      >
        {items.map((t, i) => {
          const tot = t.stance.agree + t.stance.disagree;
          const agreePct = tot > 0 ? (t.stance.agree / tot) * 100 : 50;
          const disagreePct = tot > 0 ? (t.stance.disagree / tot) * 100 : 50;

          return (
            <div key={i} className="panel" style={{ padding: 16 }}>
              {/* Status + replies */}
              <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                <Pill tone={t.open ? "amber" : "good"}>
                  {t.open ? "OPEN" : "RESOLVED"}
                </Pill>
                <Pill tone="ghost">{t.replies} replies</Pill>
              </div>

              {/* Title */}
              <div
                style={{
                  fontSize: 14.5,
                  fontWeight: 500,
                  lineHeight: 1.3,
                  marginBottom: 6,
                }}
              >
                {t.title}
              </div>

              {/* Source */}
              <div
                className="mono"
                style={{
                  fontSize: 10.5,
                  color: "var(--ink-4)",
                  marginBottom: 12,
                }}
              >
                {t.src}
              </div>

              {/* Agree/disagree bar */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    flex: 1,
                    height: 5,
                    borderRadius: 3,
                    overflow: "hidden",
                    background: "var(--line)",
                    display: "flex",
                  }}
                >
                  <div
                    style={{
                      width: `${agreePct}%`,
                      background: "var(--good)",
                    }}
                  />
                  <div
                    style={{
                      width: `${disagreePct}%`,
                      background: "var(--bad)",
                    }}
                  />
                </div>
              </div>

              {/* Counts + open thread */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 11,
                }}
              >
                <span className="mono" style={{ color: "var(--good)" }}>
                  ▲ {t.stance.agree} agree
                </span>
                <span className="mono" style={{ color: "var(--bad)" }}>
                  ▼ {t.stance.disagree} disagree
                </span>
                <div style={{ flex: 1 }} />
                <Btn size="sm" variant="ghost">
                  Open thread <Icon.Arrow />
                </Btn>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
