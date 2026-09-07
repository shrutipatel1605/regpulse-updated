/**
 * Public snippet API client.
 *
 *   POST   /snippets             — owner creates a snippet from one of their questions
 *   GET    /snippets              — owner lists their snippets
 *   GET    /snippets/{slug}      — public, returns the safe snippet (no auth)
 *   DELETE /snippets/{slug}      — owner or admin revokes
 */

import api from "@/lib/api";

export interface SnippetCitation {
  circular_number: string;
  verbatim_quote: string;
  section_reference?: string | null;
}

export interface PublicSnippetResponse {
  id: string;
  slug: string;
  snippet_text: string;
  top_citation: SnippetCitation | null;
  consult_expert: boolean;
  share_url: string;
  view_count: number;
  revoked: boolean;
  created_at: string;
}

export interface PublicSnippetView {
  slug: string;
  snippet_text: string;
  top_citation: SnippetCitation | null;
  consult_expert: boolean;
  register_cta: string;
  og_image_url: string;
  created_at: string;
}

export interface SnippetListItem {
  id: string;
  slug: string;
  question_id: string;
  snippet_text: string;
  consult_expert: boolean;
  view_count: number;
  revoked: boolean;
  created_at: string;
}

export interface SnippetListResponse {
  items: SnippetListItem[];
  total: number;
}

export async function createSnippet(question_id: string): Promise<PublicSnippetResponse> {
  const res = await api.post<PublicSnippetResponse>("/snippets", { question_id });
  return res.data;
}

export async function listMySnippets(): Promise<SnippetListResponse> {
  const res = await api.get<SnippetListResponse>("/snippets");
  return res.data;
}

export async function revokeSnippet(slug: string): Promise<{ success: boolean }> {
  const res = await api.delete<{ success: boolean }>(`/snippets/${slug}`);
  return res.data;
}

/**
 * Server-side fetch (no axios, no auth) — used by the public /s/[slug] page.
 * Reads NEXT_PUBLIC_API_URL so it works in both server and edge runtimes.
 */
export async function fetchPublicSnippet(slug: string): Promise<PublicSnippetView | null> {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  try {
    const res = await fetch(`${base}/snippets/${slug}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as PublicSnippetView;
  } catch {
    return null;
  }
}
