"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { listNews, sourceLabel, type NewsListResponse } from "@/lib/api/news";
import { RP_DATA } from "@/lib/mockData";
import { Btn, Icon, Pill } from "@/components/design/Primitives";
import type { CircularListItem, PaginatedResponse } from "@/types";

type Tab = "circ" | "news" | "cons";
type UpdatesFilter = "all" | "week" | "high";

interface UpdatesFeedResponse extends PaginatedResponse<CircularListItem> {
  unread_count: number;
}

function useUpdatesFeed(page: number, filter: UpdatesFilter, enabled: boolean) {
  return useQuery<UpdatesFeedResponse>({
    queryKey: ["circulars", "updates", page, filter],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, page_size: 20 };
      params.days = filter === "week" ? 7 : 30;
      if (filter === "high") params.impact_level = "HIGH";
      const { data } = await api.get("/circulars/updates", { params });
      return data;
    },
    staleTime: 60_000,
    enabled,
  });
}

function useMarkUpdatesSeen() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/circulars/updates/mark-seen");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["circulars", "updates-badge"] }),
  });
}

function useNews(page: number, enabled: boolean) {
  return useQuery<NewsListResponse>({
    queryKey: ["news", page],
    queryFn: () => listNews({ page, page_size: 20 }),
    staleTime: 60_000,
    enabled,
  });
}

function stripHtml(input: string | null): string {
  if (!input) return "";
  return input.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

// Mock news for fallback
const MOCK_NEWS = [
  { src: "RBI Press", title: "Governor opens ECL consultation; banks given 60 days", when: "1h ago", relevance: 92, linked: false },
  { src: "Business Standard", title: "Axis, HDFC brief RBI on digital lending guardrails", when: "3h ago", relevance: 81, linked: false },
  { src: "LiveMint", title: "SBR Upper-Layer NBFCs get 3-quarter glide path for capital build-up", when: "6h ago", relevance: 88, linked: true },
  { src: "ET Banking", title: "Priority sector shortfall filings — 9 banks expected to miss FY26", when: "Yday", relevance: 75, linked: false },
  { src: "RBI Press", title: "FEMA — ECB SOFR linkage deadline extended by 90 days", when: "Yday", relevance: 96, linked: true },
];

export default function UpdatesPage() {
  const [tab, setTab] = useState<Tab>("circ");
  const [filter, setFilter] = useState<UpdatesFilter>("all");
  const [circPage, setCircPage] = useState(1);
  const [newsPage, setNewsPage] = useState(1);

  const { data: circData, isLoading: circLoading } = useUpdatesFeed(
    circPage,
    filter,
    tab === "circ",
  );
  const { data: newsData, isLoading: newsLoading } = useNews(newsPage, tab === "news");
  const markSeen = useMarkUpdatesSeen();

  useEffect(() => {
    markSeen.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Merge live circulars with mock fallback
  const liveCircs = circData?.data ?? [];
  const displayCircs =
    liveCircs.length > 0
      ? liveCircs.map((c) => ({
          id: c.id,
          num: c.circular_number || "",
          title: c.title,
          dept: c.department || "",
          date: c.issued_date
            ? new Date(c.issued_date).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })
            : "",
          impact: (c.impact_level?.toLowerCase() || "low") as "high" | "med" | "low",
          deadline: "",
          teams: (c.tags || []).slice(0, 2),
          summary: "",
          link: `/library/${c.id}`,
        }))
      : RP_DATA.circulars
          .filter((c) => c.status === "active")
          .map((c) => ({
            id: c.id,
            num: c.num,
            title: c.title,
            dept: c.dept,
            date: c.date,
            impact: c.impact,
            deadline: c.deadline || "",
            teams: c.teams || [],
            summary: c.summary || "",
            link: "#",
          }));

  // News: live data or mock
  const liveNews = newsData?.items ?? [];
  const displayNews =
    liveNews.length > 0
      ? liveNews.map((n) => ({
          src: sourceLabel(n.source),
          title: n.title,
          when: n.published_at
            ? new Date(n.published_at).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
              })
            : "",
          relevance: n.relevance_score !== null ? Math.round(n.relevance_score * 100) : 0,
          linked: !!n.linked_circular_id,
          url: n.url,
          summary: stripHtml(n.summary),
        }))
      : MOCK_NEWS.map((n) => ({ ...n, url: "#", summary: "" }));

  const circCount = circData?.total ?? displayCircs.length;
  const newsCount = newsData?.total ?? displayNews.length;

  const tabs: [Tab, string, number][] = [
    ["circ", "RBI Circulars", circCount],
    ["news", "Market News", newsCount],
    ["cons", "Consultations", 3],
  ];

  return (
    <div className="rp-route-fade" style={{ padding: "20px 24px 60px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <h1
          className="serif"
          style={{ fontSize: 28, fontWeight: 400, letterSpacing: "-0.01em" }}
        >
          Updates
        </h1>
        <span className="live-dot" />
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>
          LAST SCAN · 2m AGO
        </span>
        <div style={{ flex: 1 }} />
        <Btn size="sm" variant="ghost">
          RSS feeds
        </Btn>
        <Btn size="sm">Subscribe to digest</Btn>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: 2,
          borderBottom: "1px solid var(--line)",
          marginBottom: 14,
        }}
      >
        {tabs.map(([id, l, n]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              padding: "8px 14px",
              fontSize: 12.5,
              fontWeight: tab === id ? 600 : 500,
              color: tab === id ? "var(--ink)" : "var(--ink-3)",
              borderBottom: `2px solid ${tab === id ? "var(--signal)" : "transparent"}`,
              background: "transparent",
              cursor: "pointer",
              border: "none",
              borderBottomWidth: 2,
              borderBottomStyle: "solid",
              borderBottomColor: tab === id ? "var(--signal)" : "transparent",
            }}
          >
            {l}{" "}
            <span className="mono" style={{ color: "var(--ink-4)", fontSize: 10, marginLeft: 4 }}>
              ({n})
            </span>
          </button>
        ))}
      </div>

      {/* Circulars tab */}
      {tab === "circ" && (
        <>
          {/* Filter chips */}
          <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
            {(
              [
                ["all", "All"],
                ["week", "This Week"],
                ["high", "High Impact"],
              ] as [UpdatesFilter, string][]
            ).map(([k, l]) => (
              <Pill
                key={k}
                tone={filter === k ? "amber" : "ghost"}
                onClick={() => {
                  setFilter(k);
                  setCircPage(1);
                }}
                style={{ cursor: "pointer" }}
              >
                {l}
              </Pill>
            ))}
          </div>

          {circLoading && (
            <div style={{ padding: 40, textAlign: "center", color: "var(--ink-4)" }}>
              Loading...
            </div>
          )}

          <div className="panel">
            <table className="dtable">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Circular</th>
                  <th>Dept</th>
                  <th>Impact</th>
                  <th>Deadline</th>
                  <th>Teams</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {displayCircs.map((c) => (
                  <tr key={c.id} style={{ cursor: "pointer" }}>
                    <td
                      className="mono tnum"
                      style={{ whiteSpace: "nowrap", fontSize: 11 }}
                    >
                      {c.date}
                    </td>
                    <td>
                      <div
                        className="mono"
                        style={{ fontSize: 10.5, color: "var(--ink-4)" }}
                      >
                        {c.num}
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 500,
                          marginTop: 2,
                          maxWidth: 520,
                        }}
                      >
                        {c.link && c.link !== "#" ? (
                          <Link
                            href={c.link}
                            style={{ color: "inherit", textDecoration: "none" }}
                          >
                            {c.title}
                          </Link>
                        ) : (
                          c.title
                        )}
                      </div>
                      {c.summary && (
                        <div
                          className="serif"
                          style={{
                            fontSize: 12.5,
                            fontStyle: "italic",
                            color: "var(--ink-3)",
                            marginTop: 4,
                            maxWidth: 520,
                          }}
                        >
                          {c.summary}
                        </div>
                      )}
                    </td>
                    <td style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{c.dept}</td>
                    <td>
                      <Pill
                        tone={
                          c.impact === "high"
                            ? "amber"
                            : c.impact === "med"
                              ? "warn"
                              : "ghost"
                        }
                      >
                        {c.impact.toUpperCase()}
                      </Pill>
                    </td>
                    <td className="mono" style={{ fontSize: 11 }}>
                      {c.deadline || "\u2014"}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
                        {c.teams.slice(0, 2).map((t) => (
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
                ))}
              </tbody>
            </table>
          </div>

          {circData && circData.total_pages > 1 && (
            <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 16 }}>
              {Array.from({ length: Math.min(circData.total_pages, 10) }, (_, i) => i + 1).map(
                (p) => (
                  <button
                    key={p}
                    onClick={() => setCircPage(p)}
                    className="btn sm"
                    style={{
                      background: p === circPage ? "var(--ink)" : "var(--panel)",
                      color: p === circPage ? "var(--bg)" : "var(--ink-3)",
                      minWidth: 32,
                    }}
                  >
                    {p}
                  </button>
                ),
              )}
            </div>
          )}
        </>
      )}

      {/* News tab */}
      {tab === "news" && (
        <>
          {newsLoading && (
            <div style={{ padding: 40, textAlign: "center", color: "var(--ink-4)" }}>
              Loading...
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {displayNews.map((n, i) => (
              <a
                key={i}
                href={n.url !== "#" ? n.url : undefined}
                target={n.url !== "#" ? "_blank" : undefined}
                rel={n.url !== "#" ? "noreferrer" : undefined}
                className="panel"
                style={{
                  padding: 14,
                  display: "grid",
                  gridTemplateColumns: "1fr auto",
                  gap: 14,
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                <div>
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      alignItems: "center",
                      marginBottom: 6,
                    }}
                  >
                    <Pill tone="blue">{n.src}</Pill>
                    {n.linked && <Pill tone="amber">Linked to circular</Pill>}
                    <span
                      className="mono"
                      style={{ fontSize: 10.5, color: "var(--ink-4)" }}
                    >
                      {n.when}
                    </span>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 500, lineHeight: 1.3 }}>
                    {n.title}
                  </div>
                  {n.summary && (
                    <div
                      style={{
                        fontSize: 12.5,
                        color: "var(--ink-3)",
                        marginTop: 4,
                        lineHeight: 1.4,
                      }}
                    >
                      {n.summary}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: "right" }}>
                  <div
                    className="mono tnum"
                    style={{ fontSize: 18, fontWeight: 600, color: "var(--signal)" }}
                  >
                    {n.relevance}
                  </div>
                  <div className="mono up" style={{ fontSize: 9, color: "var(--ink-4)" }}>
                    RELEVANCE
                  </div>
                </div>
              </a>
            ))}
          </div>

          {newsData && newsData.total > 20 && (
            <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 16 }}>
              {Array.from({ length: Math.min(Math.ceil(newsData.total / 20), 10) }, (_, i) => i + 1).map(
                (p) => (
                  <button
                    key={p}
                    onClick={() => setNewsPage(p)}
                    className="btn sm"
                    style={{
                      background: p === newsPage ? "var(--ink)" : "var(--panel)",
                      color: p === newsPage ? "var(--bg)" : "var(--ink-3)",
                      minWidth: 32,
                    }}
                  >
                    {p}
                  </button>
                ),
              )}
            </div>
          )}
        </>
      )}

      {/* Consultations tab */}
      {tab === "cons" && (
        <div className="panel" style={{ padding: 40, textAlign: "center" }}>
          <Icon.Pulse style={{ color: "var(--ink-4)", width: 32, height: 32 }} />
          <div style={{ marginTop: 10, fontSize: 13, color: "var(--ink-3)" }}>
            3 open consultations ·{" "}
            <a
              href="https://www.rbi.org.in"
              target="_blank"
              rel="noreferrer"
              style={{ color: "var(--signal)" }}
            >
              view on RBI site
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
