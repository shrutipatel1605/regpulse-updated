"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuestionHistory } from "@/hooks/useQuestions";
import { RP_DATA } from "@/lib/mockData";
import { Icon, Pill } from "@/components/design/Primitives";

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading, isError } = useQuestionHistory(page, pageSize);

  // Merge live data with mock fallback
  const liveItems = data?.data ?? [];
  const displayItems =
    liveItems.length > 0
      ? liveItems.map((q) => ({
          id: q.id,
          q: q.question_text,
          when: new Date(q.created_at).toLocaleDateString("en-IN", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          }),
          risk: (q.risk_level?.toLowerCase() || "low") as "high" | "med" | "low",
          conf: q.confidence_score ?? 0,
          teams: [] as string[],
          link: `/history/${q.id}`,
        }))
      : RP_DATA.history.map((h) => ({
          ...h,
          link: "#",
        }));

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  return (
    <div className="rp-route-fade" style={{ padding: "20px 24px 60px" }}>
      <h1
        className="serif"
        style={{ fontSize: 28, fontWeight: 400, marginBottom: 4 }}
      >
        History
      </h1>
      <p
        className="serif"
        style={{
          fontSize: 14,
          fontStyle: "italic",
          color: "var(--ink-3)",
          marginBottom: 16,
        }}
      >
        Every question you&rsquo;ve asked — with confidence, risk, and teams
        affected.
      </p>

      {isLoading && (
        <div style={{ padding: 40, textAlign: "center", color: "var(--ink-4)" }}>
          Loading history...
        </div>
      )}

      {isError && (
        <div
          style={{
            padding: "12px 14px",
            border: "1px solid var(--bad)",
            background: "var(--bad-bg)",
            borderRadius: "var(--radius)",
            fontSize: 13,
            color: "var(--bad)",
            marginBottom: 16,
          }}
        >
          Failed to load history. Showing demo data.
        </div>
      )}

      <div className="panel">
        <table className="dtable">
          <thead>
            <tr>
              <th>Question</th>
              <th style={{ width: 120 }}>When</th>
              <th style={{ width: 70 }}>Risk</th>
              <th style={{ width: 120 }}>Confidence</th>
              <th style={{ width: 180 }}>Teams</th>
              <th style={{ width: 80 }}></th>
            </tr>
          </thead>
          <tbody>
            {displayItems.map((i) => {
              const row = (
                <tr key={i.id} style={{ cursor: "pointer" }}>
                  <td style={{ fontSize: 13, fontWeight: 500, maxWidth: 500 }}>
                    {i.q}
                  </td>
                  <td
                    className="mono"
                    style={{ fontSize: 11, color: "var(--ink-3)" }}
                  >
                    {i.when}
                  </td>
                  <td>
                    <Pill
                      tone={
                        i.risk === "high"
                          ? "bad"
                          : i.risk === "med"
                            ? "warn"
                            : "good"
                      }
                    >
                      {i.risk.toUpperCase()}
                    </Pill>
                  </td>
                  <td>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <div className="bar" style={{ flex: 1 }}>
                        <span
                          style={{
                            width: `${i.conf * 100}%`,
                            background:
                              i.conf > 0.7
                                ? "var(--good)"
                                : i.conf > 0.5
                                  ? "var(--warn)"
                                  : "var(--bad)",
                          }}
                        />
                      </div>
                      <span
                        className="mono tnum"
                        style={{ fontSize: 10.5, color: "var(--ink-3)" }}
                      >
                        {Math.round(i.conf * 100)}%
                      </span>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
                      {i.teams.map((t) => (
                        <Pill key={t} tone="ghost">
                          {t}
                        </Pill>
                      ))}
                    </div>
                  </td>
                  <td>
                    <Icon.Arrow style={{ color: "var(--ink-4)" }} />
                  </td>
                </tr>
              );

              if (i.link && i.link !== "#") {
                return (
                  <Link
                    key={i.id}
                    href={i.link}
                    style={{ display: "contents", textDecoration: "none", color: "inherit" }}
                  >
                    {row}
                  </Link>
                );
              }
              return row;
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 6,
            marginTop: 16,
          }}
        >
          {Array.from({ length: Math.min(totalPages, 10) }, (_, idx) => idx + 1).map(
            (p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className="btn sm"
                style={{
                  background: p === page ? "var(--ink)" : "var(--panel)",
                  color: p === page ? "var(--bg)" : "var(--ink-3)",
                  minWidth: 32,
                }}
              >
                {p}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
