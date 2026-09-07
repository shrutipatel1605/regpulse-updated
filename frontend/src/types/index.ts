/** Shared TypeScript types for the RegPulse frontend. */

// --- Circular types ---

export interface CircularListItem {
  id: string;
  circular_number: string | null;
  title: string;
  doc_type: string;
  department: string | null;
  issued_date: string | null;
  status: string;
  impact_level: string | null;
  action_deadline: string | null;
  affected_teams: string[] | null;
  tags: string[] | null;
  regulator: string;
  indexed_at: string;
}

export interface CircularSearchResultItem extends CircularListItem {
  relevance_score: number;
  snippet: string | null;
}

export interface ChunkResponse {
  id: string;
  document_id: string;
  chunk_index: number;
  chunk_text: string;
  token_count: number;
}

export interface CircularDetail extends CircularListItem {
  effective_date: string | null;
  rbi_url: string;
  ai_summary: string | null;
  pending_admin_review: boolean;
  superseded_by: string | null;
  chunks: ChunkResponse[];
  updated_at: string;
}

// --- Question types ---

export interface CitationItem {
  circular_number: string;
  verbatim_quote: string;
  section_reference: string | null;
}

export interface RecommendedAction {
  team: string;
  action_text: string;
  priority: string;
}

export interface QuestionSummary {
  id: string;
  question_text: string;
  quick_answer: string | null;
  risk_level: string | null;
  /** 0.0–1.0; null means the question pre-dates Sprint 4 confidence persistence. */
  confidence_score: number | null;
  /** True when the answer was replaced by the "Consult an Expert" fallback. */
  consult_expert: boolean;
  model_used: string | null;
  feedback: number | null;
  credit_deducted: boolean;
  created_at: string;
}

export interface QuestionDetail extends QuestionSummary {
  answer_text: string | null;
  prompt_version: string | null;
  affected_teams: string[] | null;
  citations: CitationItem[] | null;
  recommended_actions: RecommendedAction[] | null;
  streaming_completed: boolean;
  latency_ms: number | null;
}

// --- API response wrappers ---

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SingleResponse<T> {
  success: boolean;
  data: T;
}

export interface ListResponse<T> {
  success: boolean;
  data: T[];
}

export interface QuestionResponse {
  success: boolean;
  data: QuestionDetail;
  credit_balance: number;
}

export interface AutocompleteItem {
  id: string;
  circular_number: string | null;
  title: string;
  doc_type: string;
}

// --- Filter types ---

export interface CircularFilters {
  query?: string;
  doc_type?: string;
  status?: string;
  impact_level?: string;
  department?: string;
  date_from?: string;
  date_to?: string;
  page: number;
  page_size: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// --- Error response ---

export interface ApiError {
  success: false;
  error: string;
  code: string;
}
