"use client";

import Link from "next/link";
import { Badge, impactVariant, statusVariant } from "@/components/ui/Badge";
import type { CircularListItem, CircularSearchResultItem } from "@/types";

interface CircularCardProps {
  circular: CircularListItem | CircularSearchResultItem;
}

function isSearchResult(
  c: CircularListItem | CircularSearchResultItem,
): c is CircularSearchResultItem {
  return "relevance_score" in c;
}

export function CircularCard({ circular }: CircularCardProps) {
  const formattedDate = circular.issued_date
    ? new Date(circular.issued_date).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  const fallbackDate =
    !formattedDate && !circular.department
      ? new Date(circular.indexed_at).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })
      : null;

  return (
    <Link
      href={`/library/${circular.id}`}
      className="block rounded-lg border border-gray-200 border-l-4 border-l-navy-300 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:border-l-navy-600 dark:bg-gray-900 dark:hover:shadow-none"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {circular.circular_number && (
              <span className="text-xs font-semibold text-navy-600 dark:text-navy-300">
                {circular.circular_number}
              </span>
            )}
            <Badge variant={statusVariant(circular.status)}>
              {circular.status}
            </Badge>
            {circular.impact_level && (
              <Badge variant={impactVariant(circular.impact_level)}>
                {circular.impact_level}
              </Badge>
            )}
          </div>

          <h3 className="text-sm font-medium text-gray-900 line-clamp-2 dark:text-gray-100">
            {circular.title}
          </h3>

          {isSearchResult(circular) && circular.snippet && (
            <p className="mt-2 text-xs text-gray-500 line-clamp-2 dark:text-gray-400">
              {circular.snippet}
            </p>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            {formattedDate && <span>{formattedDate}</span>}
            {circular.department && (
              <>
                {formattedDate && <span className="text-gray-300 dark:text-gray-600">|</span>}
                <span className="truncate">{circular.department}</span>
              </>
            )}
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span>{circular.doc_type.replace(/_/g, " ")}</span>
            {!formattedDate && !circular.department && fallbackDate && (
              <>
                <span className="text-gray-300 dark:text-gray-600">|</span>
                <span className="italic text-gray-400">Indexed {fallbackDate}</span>
              </>
            )}
            {isSearchResult(circular) && (
              <>
                <span className="text-gray-300 dark:text-gray-600">|</span>
                <span className="text-navy-600 dark:text-navy-300">
                  Relevance: {(circular.relevance_score * 100).toFixed(1)}%
                </span>
              </>
            )}
          </div>

          {circular.tags && circular.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {circular.tags.slice(0, 4).map((tag) => (
                <Badge key={tag} variant="default">
                  {tag}
                </Badge>
              ))}
              {circular.tags.length > 4 && (
                <span className="text-xs text-gray-400">
                  +{circular.tags.length - 4}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
