"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import type { CircularListItem } from "@/types";

function usePendingSummaries() {
  return useQuery({
    queryKey: ["admin", "circulars", "pending"],
    queryFn: async () => {
      const { data } = await api.get("/admin/circulars/pending-summaries", {
        params: { page: 1, page_size: 50 },
      });
      return data as { data: CircularListItem[]; total: number };
    },
  });
}

export default function AdminCircularsPage() {
  const { data, isLoading } = usePendingSummaries();
  const qc = useQueryClient();

  const approve = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/admin/circulars/${id}/approve-summary`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "circulars"] }),
  });

  if (isLoading) return <div className="flex justify-center p-20"><Spinner size="lg" /></div>;

  return (
    <div className="p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900">
        Pending Summaries ({data?.total ?? 0})
      </h1>
      {data?.data.length === 0 && <p className="text-sm text-gray-500">All summaries approved.</p>}
      <div className="space-y-3">
        {data?.data.map((c) => (
          <div key={c.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-navy-600">{c.circular_number}</span>
                <p className="text-sm font-medium text-gray-900 line-clamp-1">{c.title}</p>
              </div>
              <button
                onClick={() => approve.mutate(c.id)}
                disabled={approve.isPending}
                className="rounded bg-emerald-600 px-3 py-1 text-xs text-white hover:bg-emerald-700"
              >
                Approve
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
