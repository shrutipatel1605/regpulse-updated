"use client";

import { Select } from "@/components/ui/Select";
import type { CircularFilters } from "@/types";

const DOC_TYPE_OPTIONS = [
  { value: "CIRCULAR", label: "Circular" },
  { value: "MASTER_DIRECTION", label: "Master Direction" },
  { value: "NOTIFICATION", label: "Notification" },
  { value: "PRESS_RELEASE", label: "Press Release" },
  { value: "GUIDELINE", label: "Guideline" },
];

const STATUS_OPTIONS = [
  { value: "ACTIVE", label: "Active" },
  { value: "SUPERSEDED", label: "Superseded" },
  { value: "DRAFT", label: "Draft" },
];

const IMPACT_OPTIONS = [
  { value: "HIGH", label: "High Impact" },
  { value: "MEDIUM", label: "Medium Impact" },
  { value: "LOW", label: "Low Impact" },
];

const SORT_OPTIONS = [
  { value: "issued_date", label: "Issue Date" },
  { value: "indexed_at", label: "Date Indexed" },
  { value: "title", label: "Title" },
];

interface FilterPanelProps {
  filters: CircularFilters;
  onFilterChange: (key: keyof CircularFilters, value: string) => void;
  onReset: () => void;
}

export function FilterPanel({ filters, onFilterChange, onReset }: FilterPanelProps) {
  const hasActiveFilters =
    filters.doc_type || filters.status || filters.impact_level || filters.department;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Select
        value={filters.doc_type || ""}
        onChange={(v) => onFilterChange("doc_type", v)}
        options={DOC_TYPE_OPTIONS}
        placeholder="All Types"
      />

      <Select
        value={filters.status || ""}
        onChange={(v) => onFilterChange("status", v)}
        options={STATUS_OPTIONS}
        placeholder="All Statuses"
      />

      <Select
        value={filters.impact_level || ""}
        onChange={(v) => onFilterChange("impact_level", v)}
        options={IMPACT_OPTIONS}
        placeholder="All Impact Levels"
      />

      <Select
        value={filters.sort_by || "issued_date"}
        onChange={(v) => onFilterChange("sort_by", v)}
        options={SORT_OPTIONS}
        placeholder="Sort By"
      />

      <button
        onClick={() =>
          onFilterChange(
            "sort_order",
            filters.sort_order === "asc" ? "desc" : "asc",
          )
        }
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
        title={`Sort ${filters.sort_order === "asc" ? "descending" : "ascending"}`}
      >
        {filters.sort_order === "asc" ? "↑ Asc" : "↓ Desc"}
      </button>

      {hasActiveFilters && (
        <button
          onClick={onReset}
          className="rounded-lg px-3 py-2 text-sm font-medium text-navy-600 hover:bg-navy-50"
        >
          Clear Filters
        </button>
      )}
    </div>
  );
}
