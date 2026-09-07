"use client";

import { useState } from "react";

interface HeatmapProps {
  clusters: {
    id: string;
    label: string;
    question_count: number;
    representative_questions: string[];
  }[];
  time_buckets: string[];
  matrix: number[][];
}

function interpolateColor(value: number, max: number, isDark: boolean): string {
  if (max === 0 || value === 0) {
    return isDark ? "rgb(31, 41, 55)" : "rgb(249, 250, 251)"; // gray-800 / gray-50
  }
  const ratio = Math.min(value / max, 1);
  if (isDark) {
    // dark mode: gray-800 → navy-600
    const r = Math.round(31 + (30 - 31) * ratio);
    const g = Math.round(41 + (64 - 41) * ratio);
    const b = Math.round(55 + (175 - 55) * ratio);
    return `rgb(${r}, ${g}, ${b})`;
  }
  // light mode: gray-50 → navy-700
  const r = Math.round(249 + (26 - 249) * ratio);
  const g = Math.round(250 + (54 - 250) * ratio);
  const b = Math.round(251 + (148 - 251) * ratio);
  return `rgb(${r}, ${g}, ${b})`;
}

function formatDateShort(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function Heatmap({ clusters, time_buckets, matrix }: HeatmapProps) {
  const [expandedCluster, setExpandedCluster] = useState<number | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    label: string;
    date: string;
    count: number;
  } | null>(null);

  if (clusters.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        No clustering data available. Run clustering first.
      </p>
    );
  }

  // Detect dark mode
  const isDark =
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("dark");

  const maxVal = Math.max(...matrix.flat(), 1);

  return (
    <div className="overflow-x-auto">
      {/* Legend */}
      <div className="mb-3 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <span>Less</span>
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
          <div
            key={ratio}
            className="h-3 w-3 rounded-sm border border-gray-200 dark:border-gray-600"
            style={{
              backgroundColor: interpolateColor(
                ratio * maxVal,
                maxVal,
                isDark
              ),
            }}
          />
        ))}
        <span>More</span>
      </div>

      {/* Grid */}
      <div
        className="grid gap-px"
        style={{
          gridTemplateColumns: `200px repeat(${time_buckets.length}, minmax(28px, 1fr))`,
        }}
      >
        {/* Header row — date labels */}
        <div /> {/* empty top-left cell */}
        {time_buckets.map((d) => (
          <div
            key={d}
            className="text-center text-[10px] text-gray-500 dark:text-gray-400"
          >
            {formatDateShort(d)}
          </div>
        ))}

        {/* Data rows */}
        {clusters.map((cluster, ci) => (
          <>
            {/* Cluster label */}
            <div
              key={`label-${cluster.id}`}
              className="flex cursor-pointer items-center truncate pr-2 text-xs font-medium text-gray-700 hover:text-navy-700 dark:text-gray-300 dark:hover:text-navy-400"
              title={cluster.label}
              onClick={() =>
                setExpandedCluster(expandedCluster === ci ? null : ci)
              }
            >
              {cluster.label}
              <span className="ml-1 text-[10px] text-gray-400">
                ({cluster.question_count})
              </span>
            </div>

            {/* Heatmap cells */}
            {time_buckets.map((d, di) => {
              const count = matrix[ci]?.[di] ?? 0;
              return (
                <div
                  key={`${cluster.id}-${d}`}
                  className="relative h-7 rounded-sm border border-gray-100 dark:border-gray-700"
                  style={{
                    backgroundColor: interpolateColor(count, maxVal, isDark),
                  }}
                  onMouseEnter={(e) => {
                    const rect = (
                      e.target as HTMLElement
                    ).getBoundingClientRect();
                    setTooltip({
                      x: rect.left + rect.width / 2,
                      y: rect.top - 8,
                      label: cluster.label,
                      date: d,
                      count,
                    });
                  }}
                  onMouseLeave={() => setTooltip(null)}
                />
              );
            })}

            {/* Expanded representative questions */}
            {expandedCluster === ci && (
              <div
                key={`expand-${cluster.id}`}
                className="col-span-full rounded bg-gray-50 px-4 py-2 dark:bg-gray-800"
              >
                <p className="mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
                  Representative questions:
                </p>
                <ul className="list-inside list-disc space-y-0.5">
                  {cluster.representative_questions.map((q, qi) => (
                    <li
                      key={qi}
                      className="text-xs text-gray-700 dark:text-gray-300"
                    >
                      {q}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ))}
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 rounded bg-gray-900 px-2 py-1 text-xs text-white shadow-lg dark:bg-gray-100 dark:text-gray-900"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: "translate(-50%, -100%)",
          }}
        >
          {tooltip.label} &middot; {tooltip.date} &middot;{" "}
          <strong>{tooltip.count}</strong> questions
        </div>
      )}
    </div>
  );
}
