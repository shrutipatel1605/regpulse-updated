"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import toast from "react-hot-toast";

interface ScraperRun {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  documents_processed: number;
  documents_failed: number;
  error_message: string | null;
}

function useScraperRuns() {
  return useQuery({
    queryKey: ["admin", "scraper"],
    queryFn: async () => {
      const { data } = await api.get("/admin/scraper/runs", { params: { page: 1, page_size: 20 } });
      return data as { data: ScraperRun[]; total: number };
    },
  });
}

export default function ScraperPage() {
  const { data, isLoading } = useScraperRuns();
  const qc = useQueryClient();

  const trigger = useMutation({
    mutationFn: async (mode: string) => {
      const { data } = await api.post("/admin/scraper/trigger", null, { params: { mode } });
      return data;
    },
    onSuccess: (data) => {
      toast.success(data.message || "Scrape triggered");
      qc.invalidateQueries({ queryKey: ["admin", "scraper"] });
    },
  });

  if (isLoading) return <div className="flex justify-center p-20"><Spinner size="lg" /></div>;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Scraper</h1>
        <div className="flex gap-2">
          <button
            onClick={() => trigger.mutate("priority")}
            disabled={trigger.isPending}
            className="rounded bg-navy-700 px-3 py-1.5 text-xs text-white"
          >
            Priority Scrape
          </button>
          <button
            onClick={() => trigger.mutate("full")}
            disabled={trigger.isPending}
            className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-600"
          >
            Full Scrape
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {data?.data.map((run) => (
          <div key={run.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge variant={run.status === "COMPLETED" ? "active" : run.status === "FAILED" ? "high" : "medium"}>
                  {run.status}
                </Badge>
                <span className="text-xs text-gray-500">
                  {new Date(run.started_at).toLocaleString("en-IN")}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                {run.documents_processed} processed, {run.documents_failed} failed
              </div>
            </div>
            {run.error_message && (
              <p className="mt-2 text-xs text-red-600">{run.error_message}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
