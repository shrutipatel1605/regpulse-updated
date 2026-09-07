"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";

interface DashboardStats {
  total_users: number;
  active_users_30d: number;
  total_questions: number;
  questions_today: number;
  total_circulars: number;
  pending_reviews: number;
  avg_feedback_score: number | null;
  credits_consumed_30d: number;
}

function useAdminDashboard() {
  return useQuery<{ success: boolean; data: DashboardStats }>({
    queryKey: ["admin", "dashboard"],
    queryFn: async () => {
      const { data } = await api.get("/admin/dashboard");
      return data;
    },
    staleTime: 30_000,
  });
}

export default function AdminDashboardPage() {
  const { data, isLoading } = useAdminDashboard();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const stats = data?.data;

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Admin Dashboard</h1>
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Total Users" value={stats.total_users} />
          <Stat label="Active (30d)" value={stats.active_users_30d} />
          <Stat label="Total Questions" value={stats.total_questions} />
          <Stat label="Questions Today" value={stats.questions_today} />
          <Stat label="Circulars" value={stats.total_circulars} />
          <Stat label="Pending Reviews" value={stats.pending_reviews} highlight />
          <Stat
            label="Avg Feedback"
            value={stats.avg_feedback_score !== null ? stats.avg_feedback_score.toFixed(2) : "N/A"}
          />
          <Stat label="Credits Used (30d)" value={stats.credits_consumed_30d} />
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`mt-1 text-xl font-bold ${highlight ? "text-red-600" : "text-gray-900"}`}>
        {value}
      </div>
    </div>
  );
}
