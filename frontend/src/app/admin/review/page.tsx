"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import type { QuestionSummary } from "@/types";

function useFlaggedQuestions(page: number) {
  return useQuery({
    queryKey: ["admin", "review", page],
    queryFn: async () => {
      const { data } = await api.get("/admin/review", {
        params: { feedback: -1, reviewed: false, page, page_size: 20 },
      });
      return data as { data: QuestionSummary[]; total: number };
    },
  });
}

function useOverride() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, text }: { id: string; text: string }) => {
      await api.patch(`/admin/review/${id}/override`, { admin_override: text });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "review"] }),
  });
}

function useMarkReviewed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.patch(`/admin/review/${id}/mark-reviewed`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "review"] }),
  });
}

export default function ReviewPage() {
  const [page] = useState(1);
  const { data, isLoading } = useFlaggedQuestions(page);
  const override = useOverride();
  const markReviewed = useMarkReviewed();
  const [overrideText, setOverrideText] = useState<Record<string, string>>({});

  if (isLoading) return <div className="flex justify-center p-20"><Spinner size="lg" /></div>;

  return (
    <div className="p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900">
        Review Flagged Questions ({data?.total ?? 0})
      </h1>
      {data?.data.length === 0 && <p className="text-sm text-gray-500">No flagged questions.</p>}
      <div className="space-y-4">
        {data?.data.map((q) => (
          <div key={q.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-sm font-medium text-gray-900">{q.question_text}</p>
            {q.quick_answer && <p className="mt-1 text-xs text-gray-500">{q.quick_answer}</p>}
            <div className="mt-3 flex gap-2">
              <textarea
                placeholder="Override answer..."
                value={overrideText[q.id] ?? ""}
                onChange={(e) => setOverrideText((p) => ({ ...p, [q.id]: e.target.value }))}
                className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs"
                rows={2}
              />
            </div>
            <div className="mt-2 flex gap-2">
              <button
                onClick={() => override.mutate({ id: q.id, text: overrideText[q.id] ?? "" })}
                disabled={!overrideText[q.id]}
                className="rounded bg-navy-700 px-3 py-1 text-xs text-white disabled:opacity-50"
              >
                Save Override
              </button>
              <button
                onClick={() => markReviewed.mutate(q.id)}
                className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600"
              >
                Mark Reviewed
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
