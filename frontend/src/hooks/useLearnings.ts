import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export interface LearningResponse {
  id: string;
  user_id: string;
  title: string;
  note: string | null;
  source_type: string | null;
  source_id: string | null;
  source_ref: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  user_initials: string | null;
}

export function useLearnings() {
  return useQuery({
    queryKey: ["learnings"],
    queryFn: async () => {
      const { data } = await api.get<LearningResponse[]>("/learnings");
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
