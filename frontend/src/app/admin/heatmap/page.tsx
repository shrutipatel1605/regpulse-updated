"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import Heatmap from "@/components/admin/Heatmap";
import toast from "react-hot-toast";

interface ClusterInfo {
  id: string;
  label: string;
  question_count: number;
  representative_questions: string[];
}

interface HeatmapData {
  success: boolean;
  clusters: ClusterInfo[];
  time_buckets: string[];
  matrix: number[][];
}

const PERIOD_OPTIONS = [
  { label: "7 days", value: 7 },
  { label: "14 days", value: 14 },
  { label: "30 days", value: 30 },
  { label: "60 days", value: 60 },
  { label: "90 days", value: 90 },
];

export default function HeatmapPage() {
  const [periodDays, setPeriodDays] = useState(30);
  const [timeBucket, setTimeBucket] = useState<"day" | "week">("day");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "heatmap", periodDays, timeBucket],
    queryFn: async () => {
      const { data } = await api.get("/admin/dashboard/heatmap", {
        params: { period_days: periodDays, time_bucket: timeBucket },
      });
      return data as HeatmapData;
    },
  });

  const refresh = useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/admin/dashboard/heatmap/refresh", null, {
        params: { period_days: periodDays },
      });
      return data;
    },
    onSuccess: (data) => {
      toast.success(data.message || "Clustering queued");
      // Refresh data after a delay (clustering takes time)
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["admin", "heatmap"] });
      }, 3000);
    },
  });

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          Query Heatmap
        </h1>
        <button
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
          className="rounded bg-navy-700 px-3 py-1.5 text-xs text-white hover:bg-navy-800 disabled:opacity-50"
        >
          {refresh.isPending ? "Queuing..." : "Refresh Clusters"}
        </button>
      </div>

      {/* Controls */}
      <div className="mb-6 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Period:
          </label>
          <select
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
            className="rounded border border-gray-300 px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          >
            {PERIOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Group by:
          </label>
          <div className="flex rounded border border-gray-300 dark:border-gray-600">
            {(["day", "week"] as const).map((bucket) => (
              <button
                key={bucket}
                onClick={() => setTimeBucket(bucket)}
                className={`px-3 py-1 text-xs capitalize ${
                  timeBucket === bucket
                    ? "bg-navy-700 text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300"
                }`}
              >
                {bucket}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Heatmap */}
      {isLoading ? (
        <div className="flex justify-center p-20">
          <Spinner size="lg" />
        </div>
      ) : data ? (
        <Heatmap
          clusters={data.clusters}
          time_buckets={data.time_buckets}
          matrix={data.matrix}
        />
      ) : null}
    </div>
  );
}
