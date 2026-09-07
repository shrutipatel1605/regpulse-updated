"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Badge, impactVariant, statusVariant } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { useCircularDetail } from "@/hooks/useCirculars";

/** Split chunk text on "Section X.Y:" patterns and render headers. */
function formatChunkText(text: string): React.ReactNode {
  const parts = text.split(/((?:Section|Para|Clause|Article)\s+[\d.()]+\s*:)/g);

  if (parts.length <= 1) {
    return (
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700 dark:text-gray-300">
        {text}
      </p>
    );
  }

  const elements: React.ReactNode[] = [];
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i].trim();
    if (!part) continue;
    if (/^(?:Section|Para|Clause|Article)\s+[\d.()]+\s*:$/.test(part)) {
      elements.push(
        <h4
          key={i}
          className="mt-3 mb-1 text-sm font-semibold text-navy-700 dark:text-navy-300"
        >
          {part}
        </h4>,
      );
    } else {
      elements.push(
        <p
          key={i}
          className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700 dark:text-gray-300"
        >
          {part}
        </p>,
      );
    }
  }
  return <>{elements}</>;
}

export default function CircularDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const { data, isLoading, isError } = useCircularDetail(id);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="px-6 py-6 lg:px-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          Circular not found or failed to load.
        </div>
        <Link
          href="/library"
          className="mt-4 inline-block text-sm font-medium text-navy-600 hover:text-navy-700 dark:text-navy-300"
        >
          Back to Library
        </Link>
      </div>
    );
  }

  const circular = data.data;
  const formattedIssuedDate = circular.issued_date
    ? new Date(circular.issued_date).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;
  const formattedEffectiveDate = circular.effective_date
    ? new Date(circular.effective_date).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  const hasMetadata =
    formattedIssuedDate ||
    formattedEffectiveDate ||
    circular.department ||
    circular.action_deadline;

  return (
    <div className="px-6 py-6 lg:px-8">
      {/* Back link */}
      <Link
        href="/library"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Library
      </Link>

      {/* Header */}
      <div className="mb-6">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {circular.circular_number && (
            <span className="text-sm font-semibold text-navy-600 dark:text-navy-300">
              {circular.circular_number}
            </span>
          )}
          <Badge variant={statusVariant(circular.status)}>{circular.status}</Badge>
          {circular.impact_level && (
            <Badge variant={impactVariant(circular.impact_level)}>
              {circular.impact_level} Impact
            </Badge>
          )}
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {circular.doc_type.replace(/_/g, " ")}
          </span>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-50">
          {circular.title}
        </h1>
      </div>

      {/* Metadata grid — only render when we have data */}
      {hasMetadata && (
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {formattedIssuedDate && (
            <MetadataCard label="Issued Date" value={formattedIssuedDate} />
          )}
          {formattedEffectiveDate && (
            <MetadataCard label="Effective Date" value={formattedEffectiveDate} />
          )}
          {circular.department && (
            <MetadataCard label="Department" value={circular.department} />
          )}
          {circular.action_deadline && (
            <MetadataCard
              label="Action Deadline"
              value={new Date(circular.action_deadline).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
            />
          )}
        </div>
      )}

      {/* Affected teams */}
      {circular.affected_teams && circular.affected_teams.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
            Affected Teams
          </h2>
          <div className="flex flex-wrap gap-2">
            {circular.affected_teams.map((team) => (
              <Badge key={team}>{team}</Badge>
            ))}
          </div>
        </div>
      )}

      {/* Tags */}
      {circular.tags && circular.tags.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Tags</h2>
          <div className="flex flex-wrap gap-2">
            {circular.tags.map((tag) => (
              <Badge key={tag}>{tag}</Badge>
            ))}
          </div>
        </div>
      )}

      {/* AI Summary */}
      {circular.ai_summary && !circular.pending_admin_review && (
        <div className="mb-8 rounded-lg border border-navy-100 bg-navy-50 p-5 dark:border-navy-800 dark:bg-navy-900/30">
          <h2 className="mb-2 text-sm font-semibold text-navy-700 dark:text-navy-300">
            AI Summary
          </h2>
          <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
            {circular.ai_summary}
          </p>
        </div>
      )}

      {circular.pending_admin_review && (
        <div className="mb-8 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
          AI summary is pending admin review.
        </div>
      )}

      {/* Source link */}
      <div className="mb-8">
        <a
          href={circular.rbi_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm font-medium text-navy-600 hover:text-navy-700 dark:text-navy-300 dark:hover:text-navy-200"
        >
          View on RBI website
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
            />
          </svg>
        </a>
      </div>

      {/* Text chunks */}
      {circular.chunks.length > 0 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-50">
            Document Content ({circular.chunks.length} sections)
          </h2>
          <div className="space-y-4">
            {circular.chunks
              .sort((a, b) => a.chunk_index - b.chunk_index)
              .map((chunk) => (
                <div
                  key={chunk.id}
                  className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
                >
                  <div className="mb-2">
                    <span className="text-xs font-medium text-gray-400 dark:text-gray-500">
                      Part {chunk.chunk_index + 1}
                    </span>
                  </div>
                  {formatChunkText(chunk.chunk_text)}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetadataCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</div>
      <div className="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">{value}</div>
    </div>
  );
}
