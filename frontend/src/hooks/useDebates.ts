import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export interface DebateReplyResponse {
  id: string;
  thread_id: string;
  user_id: string;
  content: string;
  refs_count: number;
  created_at: string;
  updated_at: string;
  who: string;
  role: string;
}

export interface DebateThreadResponse {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  status: "OPEN" | "RESOLVED";
  source_circular_id: string | null;
  source_ref: string | null;
  tags: string[];
  stance_agree: number;
  stance_disagree: number;
  created_at: string;
  updated_at: string;
  replies: DebateReplyResponse[];
}

export function useDebates() {
  return useQuery({
    queryKey: ["debates"],
    queryFn: async () => {
      const { data } = await api.get<DebateThreadResponse[]>("/debates");
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
