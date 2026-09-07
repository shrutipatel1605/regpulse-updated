"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { RP_DATA } from "@/lib/mockData";
import { Avatar, Btn, Icon, MiniStat, Pill, useToast } from "@/components/design/Primitives";

interface ActionItem {
  id: string;
  title: string;
  description: string | null;
  assigned_team: string | null;
  priority: string;
  due_date: string | null;
  status: string;
  created_at: string;
}

function useActionItems(page: number, status?: string) {
  return useQuery({
    queryKey: ["action-items", page, status],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, page_size: 20 };
      if (status) params.status = status;
      const { data } = await api.get("/action-items", { params });
      return data as { data: ActionItem[]; total: number; page: number; page_size: number };
    },
  });
}

function useUpdateStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      await api.patch(`/action-items/${id}`, { status });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["action-items"] }),
  });
}

type FilterKey = "all" | "open" | "in-progress" | "pending" | "done";

export default function ActionItemsPage() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<FilterKey>("all");

  // Map filter to API status param
  const apiStatus =
    filter === "all"
      ? undefined
      : filter === "open"
        ? undefined // "open" = not COMPLETED, handled client-side
        : filter === "in-progress"
          ? "IN_PROGRESS"
          : filter === "pending"
            ? "PENDING"
            : "COMPLETED";

  const { data, isLoading } = useActionItems(page, apiStatus);
  const updateStatus = useUpdateStatus();

  // Merge live data with mock fallback
  const liveItems = data?.data ?? [];
  const displayItems =
    liveItems.length > 0
      ? liveItems.map((i) => ({
          id: i.id,
          title: i.title,
          team: i.assigned_team || "",
          priority: (i.priority?.toLowerCase() || "low") as "high" | "med" | "low",
          due: i.due_date
            ? new Date(i.due_date).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })
            : "",
          status: i.status.toLowerCase().replace("_", "-") as
            | "pending"
            | "in-progress"
            | "done"
            | "completed",
          owner: (i.assigned_team || "??").slice(0, 2).toUpperCase(),
          src: "",
          isLive: true,
          rawStatus: i.status,
        }))
      : RP_DATA.actionItems.map((i) => ({
          ...i,
          isLive: false,
          rawStatus: i.status.toUpperCase().replace("-", "_"),
        }));

  // Client-side "open" filter (not done)
  const filtered =
    filter === "open"
      ? displayItems.filter(
          (i) => i.status !== "done" && i.status !== "completed",
        )
      : displayItems;

  // Stats
  const allItems = displayItems;
  const stats = {
    total: allItems.length,
    done: allItems.filter(
      (i) => i.status === "done" || i.status === "completed",
    ).length,
    high: allItems.filter(
      (i) =>
        i.priority === "high" &&
        i.status !== "done" &&
        i.status !== "completed",
    ).length,
    overdue: liveItems.length > 0
      ? liveItems.filter(
          (i) =>
            i.due_date &&
            new Date(i.due_date) < new Date() &&
            i.status !== "COMPLETED",
        ).length
      : 1,
  };

  const tabs: [FilterKey, string, number][] = [
    ["all", "All", allItems.length],
    [
      "open",
      "Open",
      allItems.filter(
        (i) => i.status !== "done" && i.status !== "completed",
      ).length,
    ],
    [
      "in-progress",
      "In progress",
      allItems.filter((i) => i.status === "in-progress").length,
    ],
    ["pending", "Pending", allItems.filter((i) => i.status === "pending").length],
    [
      "done",
      "Done",
      allItems.filter(
        (i) => i.status === "done" || i.status === "completed",
      ).length,
    ],
  ];

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  const toggleStatus = (item: (typeof displayItems)[number]) => {
    if (!item.isLive) {
      toast.push({ tag: "ACTION", text: "Demo mode — status not persisted." });
      return;
    }
    const nextStatus =
      item.rawStatus === "PENDING"
        ? "IN_PROGRESS"
        : item.rawStatus === "IN_PROGRESS"
          ? "COMPLETED"
          : "PENDING";
    updateStatus.mutate({ id: item.id, status: nextStatus });
  };

  return (
    <div className="rp-route-fade" style={{ padding: "20px 24px 60px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: 14,
          marginBottom: 16,
        }}
      >
        <div>
          <h1 className="serif" style={{ fontSize: 28, fontWeight: 400 }}>
            Action Items
          </h1>
          <p
            className="serif"
            style={{
              fontSize: 14,
              fontStyle: "italic",
              color: "var(--ink-3)",
              marginTop: 4,
            }}
          >
            Tasks extracted from briefs and circulars — assigned to teams,
            tracked to close.
          </p>
        </div>
        <div style={{ flex: 1 }} />
        <MiniStat label="OPEN" value={stats.total - stats.done} />
        <MiniStat label="HIGH" value={stats.high} signal />
        <MiniStat label="OVERDUE" value={stats.overdue} tone="bad" />
        <Btn variant="primary">
          <Icon.Plus /> New action
        </Btn>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: 6,
          marginBottom: 14,
          borderBottom: "1px solid var(--line)",
        }}
      >
        {tabs.map(([k, l, n]) => (
          <button
            key={k}
            onClick={() => {
              setFilter(k);
              setPage(1);
            }}
            style={{
              padding: "7px 12px",
              fontSize: 12,
              fontWeight: filter === k ? 600 : 400,
              color: filter === k ? "var(--ink)" : "var(--ink-3)",
              borderBottom: `2px solid ${filter === k ? "var(--signal)" : "transparent"}`,
              background: "transparent",
              cursor: "pointer",
              border: "none",
              borderBottomWidth: 2,
              borderBottomStyle: "solid",
              borderBottomColor: filter === k ? "var(--signal)" : "transparent",
            }}
          >
            {l}{" "}
            <span className="mono" style={{ color: "var(--ink-4)", fontSize: 10 }}>
              {n}
            </span>
          </button>
        ))}
      </div>

      {isLoading && (
        <div style={{ padding: 40, textAlign: "center", color: "var(--ink-4)" }}>
          Loading...
        </div>
      )}

      {/* Table */}
      <div className="panel">
        <table className="dtable">
          <thead>
            <tr>
              <th style={{ width: 32 }}></th>
              <th style={{ width: 60 }}>Prio</th>
              <th>Title</th>
              <th style={{ width: 100 }}>Team</th>
              <th style={{ width: 70 }}>Owner</th>
              <th style={{ width: 100 }}>Due</th>
              <th style={{ width: 120 }}>Source</th>
              <th style={{ width: 80 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((i) => {
              const isDone =
                i.status === "done" || i.status === "completed";
              return (
                <tr key={i.id}>
                  <td>
                    <input
                      type="checkbox"
                      className="checkbox"
                      checked={isDone}
                      onChange={() => toggleStatus(i)}
                    />
                  </td>
                  <td>
                    <Pill
                      tone={
                        i.priority === "high"
                          ? "bad"
                          : i.priority === "med"
                            ? "warn"
                            : "ghost"
                      }
                    >
                      {i.priority.toUpperCase()}
                    </Pill>
                  </td>
                  <td
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      textDecoration: isDone ? "line-through" : "none",
                      color: isDone ? "var(--ink-4)" : "var(--ink)",
                    }}
                  >
                    {i.title}
                  </td>
                  <td className="mono" style={{ fontSize: 11 }}>
                    {i.team}
                  </td>
                  <td>
                    <Avatar initials={i.owner} size={22} />
                  </td>
                  <td className="mono tnum" style={{ fontSize: 11 }}>
                    {i.due}
                  </td>
                  <td>
                    <span
                      className="mono"
                      style={{ fontSize: 10.5, color: "var(--signal)" }}
                    >
                      {i.src}
                    </span>
                  </td>
                  <td>
                    <Pill
                      tone={
                        isDone
                          ? "good"
                          : i.status === "in-progress"
                            ? "amber"
                            : "ghost"
                      }
                    >
                      {i.status.replace("-", " ").toUpperCase()}
                    </Pill>
                  </td>
                </tr>
              );
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
