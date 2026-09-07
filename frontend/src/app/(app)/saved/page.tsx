"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { RP_DATA } from "@/lib/mockData";
import { Btn, Icon, Pill } from "@/components/design/Primitives";

interface SavedItem {
  id: string;
  question_id: string;
  name: string;
  tags: string[] | null;
  needs_review: boolean;
  created_at: string;
}

function useSavedList(page: number) {
  return useQuery({
    queryKey: ["saved", page],
    queryFn: async () => {
      const { data } = await api.get("/saved", { params: { page, page_size: 20 } });
      return data as { data: SavedItem[]; total: number; page: number };
    },
  });
}

function useDeleteSaved() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/saved/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved"] }),
  });
}

export default function SavedPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useSavedList(page);
  const deleteSaved = useDeleteSaved();

  // Merge live data with mock fallback
  const liveItems = data?.data ?? [];
  const displayItems =
    liveItems.length > 0
      ? liveItems.map((s) => ({
          id: s.id,
          questionId: s.question_id,
          title: s.name,
          q: "",
          when: new Date(s.created_at).toLocaleDateString("en-IN", {
            day: "numeric",
            month: "short",
            year: "numeric",
          }),
          tags: s.tags || [],
          needsReview: s.needs_review,
          isLive: true,
        }))
      : RP_DATA.saved.map((s) => ({
          id: s.id,
          questionId: "",
          title: s.title,
          q: s.q,
          when: s.when,
          tags: s.tags,
          needsReview: false,
          isLive: false,
        }));

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <div className="rp-route-fade" style={{ padding: "20px 24px 60px" }}>
      <h1
        className="serif"
        style={{ fontSize: 28, fontWeight: 400, marginBottom: 4 }}
      >
        Saved Interpretations
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
        Briefs you&rsquo;ve bookmarked for fast recall during board and
        regulator reviews.
      </p>

      {isLoading && (
        <div style={{ padding: 40, textAlign: "center", color: "var(--ink-4)" }}>
          Loading...
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
        }}
      >
        {displayItems.map((s) => {
          const card = (
            <div
              key={s.id}
              className="panel"
              style={{ padding: 14, cursor: "pointer" }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 8,
                }}
              >
                <Icon.Bookmark style={{ color: "var(--signal)" }} />
                <span
                  className="mono"
                  style={{ fontSize: 10.5, color: "var(--ink-4)" }}
                >
                  {s.when}
                </span>
                {s.needsReview && <Pill tone="bad">REVIEW</Pill>}
                <div style={{ flex: 1 }} />
                {s.isLive && (
                  <Btn
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      deleteSaved.mutate(s.id);
                    }}
                    style={{ color: "var(--bad)" }}
                  >
                    <Icon.Close /> Remove
                  </Btn>
                )}
              </div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  lineHeight: 1.3,
                  marginBottom: 6,
                }}
              >
                {s.title}
              </div>
              {s.q && (
                <div
                  className="serif"
                  style={{
                    fontSize: 12.5,
                    fontStyle: "italic",
                    color: "var(--ink-3)",
                    marginBottom: 10,
                  }}
                >
                  &ldquo;{s.q}&rdquo;
                </div>
              )}
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {s.tags.map((t) => (
                  <Pill key={t} tone="ghost">
                    {t}
                  </Pill>
                ))}
              </div>
            </div>
          );

          if (s.isLive && s.questionId) {
            return (
              <Link
                key={s.id}
                href={`/history/${s.questionId}`}
                style={{ textDecoration: "none", color: "inherit" }}
              >
                {card}
              </Link>
            );
          }
          return card;
        })}
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
