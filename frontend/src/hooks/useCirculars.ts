"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  AutocompleteItem,
  CircularDetail,
  CircularFilters,
  CircularListItem,
  CircularSearchResultItem,
  ListResponse,
  PaginatedResponse,
  SingleResponse,
} from "@/types";

/** Fetch paginated circular list with filters. */
export function useCircularList(filters: CircularFilters) {
  return useQuery<PaginatedResponse<CircularListItem>>({
    queryKey: ["circulars", "list", filters],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        page: filters.page,
        page_size: filters.page_size,
      };
      if (filters.doc_type) params.doc_type = filters.doc_type;
      if (filters.status) params.status = filters.status;
      if (filters.impact_level) params.impact_level = filters.impact_level;
      if (filters.department) params.department = filters.department;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      if (filters.sort_by) params.sort_by = filters.sort_by;
      if (filters.sort_order) params.sort_order = filters.sort_order;

      const { data } = await api.get<PaginatedResponse<CircularListItem>>(
        "/circulars",
        { params },
      );
      return data;
    },
    staleTime: 30_000,
  });
}

/** Hybrid search for circulars (requires auth). */
export function useCircularSearch(
  query: string,
  filters: Omit<CircularFilters, "query">,
  enabled: boolean = true,
) {
  return useQuery<PaginatedResponse<CircularSearchResultItem>>({
    queryKey: ["circulars", "search", query, filters],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        query,
        page: filters.page,
        page_size: filters.page_size,
      };
      if (filters.doc_type) params.doc_type = filters.doc_type;
      if (filters.status) params.status = filters.status;
      if (filters.impact_level) params.impact_level = filters.impact_level;
      if (filters.department) params.department = filters.department;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;

      const { data } = await api.get<PaginatedResponse<CircularSearchResultItem>>(
        "/circulars/search",
        { params },
      );
      return data;
    },
    enabled: enabled && query.length >= 3,
    staleTime: 60_000,
  });
}

/** Autocomplete suggestions. */
export function useCircularAutocomplete(q: string, enabled: boolean = true) {
  return useQuery<ListResponse<AutocompleteItem>>({
    queryKey: ["circulars", "autocomplete", q],
    queryFn: async () => {
      const { data } = await api.get<ListResponse<AutocompleteItem>>(
        "/circulars/autocomplete",
        { params: { q, limit: 10 } },
      );
      return data;
    },
    enabled: enabled && q.length >= 1,
    staleTime: 10_000,
  });
}

/** Fetch single circular detail. */
export function useCircularDetail(id: string) {
  return useQuery<SingleResponse<CircularDetail>>({
    queryKey: ["circulars", "detail", id],
    queryFn: async () => {
      const { data } = await api.get<SingleResponse<CircularDetail>>(
        `/circulars/${id}`,
      );
      return data;
    },
    enabled: !!id,
    staleTime: 60_000,
  });
}

/** Fetch department list for filter dropdown. */
export function useDepartments() {
  return useQuery<ListResponse<string>>({
    queryKey: ["circulars", "departments"],
    queryFn: async () => {
      const { data } = await api.get<ListResponse<string>>("/circulars/departments");
      return data;
    },
    staleTime: 300_000,
  });
}

/** Fetch tag list for filter dropdown. */
export function useTags() {
  return useQuery<ListResponse<string>>({
    queryKey: ["circulars", "tags"],
    queryFn: async () => {
      const { data } = await api.get<ListResponse<string>>("/circulars/tags");
      return data;
    },
    staleTime: 300_000,
  });
}

/** Fetch doc type list for filter dropdown. */
export function useDocTypes() {
  return useQuery<ListResponse<string>>({
    queryKey: ["circulars", "doc-types"],
    queryFn: async () => {
      const { data } = await api.get<ListResponse<string>>("/circulars/doc-types");
      return data;
    },
    staleTime: 300_000,
  });
}
