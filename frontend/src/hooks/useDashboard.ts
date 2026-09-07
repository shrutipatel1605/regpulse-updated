import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export interface DashboardPulseResponse {
  success: boolean;
  pulse: {
    total_circulars: number;
    this_week: number;
    superseded: number;
    questions_asked: number;
    questions_answered: number;
    learnings_captured: number;
    sparkline: number[];
  };
  heatmap: {
    cols: string[];
    rows: Array<{ name: string; vals: number[] }>;
  };
  activity: Array<{
    when: string;
    type: "circ" | "ask" | "save" | "learn" | "debate";
    text: string;
    impact?: "high" | "med" | "low";
  }>;
}

export function useDashboardPulse() {
  return useQuery({
    queryKey: ["dashboard", "pulse"],
    queryFn: async () => {
      const { data } = await api.get<DashboardPulseResponse>("/dashboard/pulse");
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
