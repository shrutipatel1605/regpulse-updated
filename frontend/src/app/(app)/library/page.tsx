"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { useCircularList, useCircularSearch } from "@/hooks/useCirculars";
import { useAuthStore } from "@/stores/authStore";
import { RP_DATA } from "@/lib/mockData";
import { Icon, Pill } from "@/components/design/Primitives";
import type { CircularFilters } from "@/types";

const DEFAULT_FILTERS: CircularFilters = {
  page: 1,
  page_size: 20,
  sort_by: "issued_date",
  sort_order: "desc",
};

export default function LibraryPage() {
  const [filters, setFilters] = useState<CircularFilters>(DEFAULT_FILTERS);
  const [searchQuery, setSearchQuery] = useState("");
  const [impactFilter, setImpactFilter] = useState("all");
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const isSearchMode = searchQuery.length >= 3;

  const listQuery = useCircularList(filters);
  const searchResults = useCircularSearch(
    searchQuery,
    { ...filters, page: filters.page, page_size: filters.page_size },
    isSearchMode && isAuthenticated,
  );

  const activeQuery = isSearchMode && isAuthenticated ? searchResults : listQuery;
  const { data, isLoading, isError } = activeQuery;

  const handleFilterChange = useCallback(
    (key: keyof CircularFilters, value: string) => {
      setFilters((prev) => ({
        ...prev,
        [key]: value || undefined,
        page: key === "page" ? Number(value) || 1 : 1,
      }));
    },
    [],
  );

  const handlePageChange = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }));
  }, []);

  // Merge live data with mock fallback
  const liveCirculars = data?.data ?? [];
  const displayCirculars =
    liveCirculars.length > 0
      ? liveCirculars.map((c) => ({
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
          status: (c.status?.toLowerCase() || "active") as "active" | "superseded",
          tags: c.tags || [],
          summary: "",
          link: `/library/${c.id}`,
        }))
      : RP_DATA.circulars.map((c) => ({
          ...c,
          link: "#",
        }));

  const filtered =
    impactFilter === "all"
      ? displayCirculars
      : displayCirculars.filter((c) => c.impact === impactFilter);

  return (
    <div
      className="rp-route-fade"
      style={{ display: "grid", gridTemplateColumns: "240px 1fr", height: "100%" }}
    >
      {/* Filter aside */}
      <aside
        style={{
          borderRight: "1px solid var(--line)",
          background: "var(--panel)",
          padding: "18px 16px",
          overflowY: "auto",
        }}
      >
        <div className="tick" style={{ marginBottom: 10 }}>
          FILTERS
        </div>
        <div
          className="mono up"
          style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 6 }}
        >
          IMPACT
        </div>
        {(
          [
            ["all", "All"],
            ["high", "High"],
            ["med", "Medium"],
            ["low", "Low"],
          ] as const
        ).map(([k, l]) => (
          <label
            key={k}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "3px 0",
              fontSize: 12.5,
              cursor: "pointer",
            }}
          >
            <input
              type="radio"
              checked={impactFilter === k}
              onChange={() => setImpactFilter(k)}
              className="checkbox"
              style={{ borderRadius: "50%" }}
            />
            {l}
          </label>
        ))}
        <div
          className="mono up"
          style={{ fontSize: 10, color: "var(--ink-4)", margin: "14px 0 6px" }}
        >
          DEPARTMENT
        </div>
        {["Dept. of Regulation", "Foreign Exchange", "DPSS", "Consumer Education"].map(
          (d) => (
            <label
              key={d}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "3px 0",
                fontSize: 12.5,
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                className="checkbox"
                defaultChecked={d.startsWith("Dept")}
                onChange={(e) => {
                  if (d.startsWith("Dept")) {
                    handleFilterChange(
                      "department" as keyof CircularFilters,
                      e.target.checked ? "" : "none",
                    );
                  }
                }}
              />{" "}
              {d}
            </label>
          ),
        )}
        <div
          className="mono up"
          style={{ fontSize: 10, color: "var(--ink-4)", margin: "14px 0 6px" }}
        >
          DATE
        </div>
        {["Last 7 days", "Last 30 days", "FY26", "FY25"].map((d) => (
          <label
            key={d}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "3px 0",
              fontSize: 12.5,
              cursor: "pointer",
            }}
          >
            <input type="checkbox" className="checkbox" /> {d}
          </label>
        ))}
        <div
          className="mono up"
          style={{ fontSize: 10, color: "var(--ink-4)", margin: "14px 0 6px" }}
        >
          STATUS
        </div>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "3px 0",
            fontSize: 12.5,
            cursor: "pointer",
          }}
        >
          <input type="checkbox" className="checkbox" defaultChecked /> Active only
        </label>
      </aside>

      {/* Main content */}
      <div style={{ padding: "20px 24px", overflowY: "auto" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 16,
          }}
        >
          <h1
            className="serif"
            style={{ fontSize: 26, fontWeight: 400 }}
          >
            Circular Library
          </h1>
          <span
            className="mono"
            style={{ fontSize: 11, color: "var(--ink-4)" }}
          >
            {data
              ? `${data.total.toLocaleString()} indexed`
              : `${RP_DATA.pulse.totalCirculars.toLocaleString()} indexed`}{" "}
            · {RP_DATA.pulse.superseded} superseded this week
          </span>
          <div style={{ flex: 1 }} />
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              border: "1px solid var(--line)",
              background: "var(--panel)",
              padding: "6px 10px",
              borderRadius: 3,
              minWidth: 320,
            }}
          >
            <Icon.Search style={{ color: "var(--ink-4)" }} />
            <input
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setFilters((prev) => ({ ...prev, page: 1 }));
              }}
              placeholder="Search circular number, title, section..."
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                fontSize: 12.5,
              }}
            />
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div style={{ padding: 40, textAlign: "center", color: "var(--ink-4)" }}>
            Loading circulars...
          </div>
        )}

        {/* Error */}
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
            Failed to load circulars. Showing demo data.
          </div>
        )}

        {/* 2-col card grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
          }}
        >
          {filtered.map((c) => (
            <CircCard key={c.id} c={c} />
          ))}
        </div>

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 6,
              marginTop: 20,
            }}
          >
            {Array.from({ length: Math.min(data.total_pages, 10) }, (_, i) => i + 1).map(
              (p) => (
                <button
                  key={p}
                  onClick={() => handlePageChange(p)}
                  className="btn sm"
                  style={{
                    background:
                      p === (data.page || filters.page)
                        ? "var(--ink)"
                        : "var(--panel)",
                    color:
                      p === (data.page || filters.page)
                        ? "var(--bg)"
                        : "var(--ink-3)",
                    minWidth: 32,
                    textAlign: "center",
                  }}
                >
                  {p}
                </button>
              ),
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── CircCard ──────────────────────────────────────────────────────────── */

function CircCard({
  c,
}: {
  c: {
    id: string;
    num: string;
    title: string;
    impact: "high" | "med" | "low";
    status: "active" | "superseded";
    date: string;
    tags: string[];
    summary?: string;
    link?: string;
  };
}) {
  const inner = (
    <div
      className="panel"
      style={{
        padding: 14,
        cursor: "pointer",
        transition: "border-color .12s",
      }}
      onMouseOver={(e) =>
        (e.currentTarget.style.borderColor = "var(--ink-4)")
      }
      onMouseOut={(e) =>
        (e.currentTarget.style.borderColor = "var(--line)")
      }
    >
      <div
        style={{
          display: "flex",
          gap: 6,
          marginBottom: 8,
          alignItems: "center",
        }}
      >
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
        {c.status === "superseded" && <Pill tone="bad">SUPERSEDED</Pill>}
        <span style={{ flex: 1 }} />
        <span
          className="mono tnum"
          style={{ fontSize: 10.5, color: "var(--ink-4)" }}
        >
          {c.date}
        </span>
      </div>
      <div
        className="mono"
        style={{ fontSize: 10.5, color: "var(--ink-4)", marginBottom: 4 }}
      >
        {c.num}
      </div>
      <div
        style={{
          fontSize: 13,
          fontWeight: 500,
          lineHeight: 1.3,
          marginBottom: 8,
          color: "var(--ink)",
        }}
      >
        {c.title}
      </div>
      {c.summary && (
        <div
          className="serif"
          style={{
            fontSize: 12.5,
            fontStyle: "italic",
            color: "var(--ink-3)",
            lineHeight: 1.4,
            marginBottom: 10,
          }}
        >
          {c.summary}
        </div>
      )}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        {c.tags.map((t) => (
          <Pill key={t} tone="ghost">
            {t}
          </Pill>
        ))}
      </div>
    </div>
  );

  if (c.link && c.link !== "#") {
    return (
      <Link href={c.link} style={{ textDecoration: "none", color: "inherit" }}>
        {inner}
      </Link>
    );
  }
  return inner;
}
