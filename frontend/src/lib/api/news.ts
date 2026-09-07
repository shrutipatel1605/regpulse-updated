/**
 * News feed API client (Sprint 3 Pillar B).
 */

import api from "@/lib/api";

export interface NewsItemSummary {
  id: string;
  source: string;
  title: string;
  url: string;
  published_at: string | null;
  summary: string | null;
  relevance_score: number | null;
  status: string;
  linked_circular_id: string | null;
  created_at: string;
}

export interface NewsListResponse {
  items: NewsItemSummary[];
  total: number;
  page: number;
  page_size: number;
}

export async function listNews(params: {
  page?: number;
  page_size?: number;
  source?: string;
  only_linked?: boolean;
}): Promise<NewsListResponse> {
  const res = await api.get<NewsListResponse>("/news", { params });
  return res.data;
}

const SOURCE_LABELS: Record<string, string> = {
  RBI_PRESS: "RBI Press",
  BUSINESS_STANDARD: "Business Standard",
  LIVEMINT: "LiveMint",
  ET_BANKING: "ET Banking",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}
