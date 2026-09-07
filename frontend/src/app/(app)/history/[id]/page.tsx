"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { ShareSnippetDialog } from "@/components/ShareSnippetDialog";
import { Badge, impactVariant } from "@/components/ui/Badge";
import { ConfidenceMeter } from "@/components/ui/ConfidenceMeter";
import { Spinner } from "@/components/ui/Spinner";
import { trackEvent } from "@/lib/analytics";
import { useQuestionDetail, useSubmitFeedback } from "@/hooks/useQuestions";

export default function QuestionDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [shareOpen, setShareOpen] = useState(false);

  const { data, isLoading, isError } = useQuestionDetail(id);
  const feedbackMutation = useSubmitFeedback();

  // Fire `confidence_meter_viewed` once per question, after the data
  // resolves. The `firedFor` ref guards against the analytics event
  // being re-emitted on every re-render of the same question.
  const firedForRef = useRef<string | null>(null);
  useEffect(() => {
    if (!data?.data) return;
    if (firedForRef.current === data.data.id) return;
    firedForRef.current = data.data.id;
    if (
      data.data.confidence_score !== null ||
      data.data.consult_expert
    ) {
      trackEvent("confidence_meter_viewed", {
        confidence_score: data.data.confidence_score,
        consult_expert: data.data.consult_expert,
        source: "history_detail",
      });
    }
  }, [data]);

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
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Question not found or failed to load.
        </div>
        <Link
          href="/history"
          className="mt-4 inline-block text-sm font-medium text-navy-600"
        >
          Back to History
        </Link>
      </div>
    );
  }

  const q = data.data;

  return (
    <div className="px-6 py-6 lg:px-8">
      {/* Back link */}
      <Link
        href="/history"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to History
      </Link>

      {/* Question */}
      <div className="mb-6">
        <h1 className="text-lg font-bold text-gray-900">{q.question_text}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {q.risk_level && (
            <Badge variant={impactVariant(q.risk_level)}>
              Risk: {q.risk_level}
            </Badge>
          )}
          {q.model_used && (
            <span className="text-xs text-gray-400">{q.model_used}</span>
          )}
          <span className="text-xs text-gray-400">
            {new Date(q.created_at).toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          {q.latency_ms && (
            <span className="text-xs text-gray-400">{q.latency_ms}ms</span>
          )}
        </div>
      </div>

      {/* Confidence meter (Sprint 4 — only present on questions persisted
          after the migration; older questions render nothing) */}
      {(q.confidence_score !== null || q.consult_expert) && (
        <div className="mb-6">
          <ConfidenceMeter
            score={q.confidence_score}
            consultExpert={q.consult_expert}
          />
        </div>
      )}

      {/* Quick answer */}
      {q.quick_answer && (
        <div className="mb-6 rounded-lg border border-navy-100 bg-navy-50 p-4 dark:border-navy-800 dark:bg-navy-900/40">
          <h3 className="mb-1 text-xs font-semibold uppercase text-navy-600 dark:text-navy-300">
            Quick Answer
          </h3>
          <p className="text-sm text-gray-800 dark:text-gray-100">{q.quick_answer}</p>
        </div>
      )}

      {/* Affected teams */}
      {q.affected_teams && q.affected_teams.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {q.affected_teams.map((team) => (
            <Badge key={team}>{team}</Badge>
          ))}
        </div>
      )}

      {/* Full answer */}
      {q.answer_text && (
        <div className="prose prose-sm mb-8 max-w-none">
          <ReactMarkdown>{q.answer_text}</ReactMarkdown>
        </div>
      )}

      {/* Citations */}
      {q.citations && q.citations.length > 0 && (
        <div className="mb-8">
          <h3 className="mb-2 text-sm font-semibold text-gray-700">
            Citations
          </h3>
          <div className="space-y-2">
            {q.citations.map((c, i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-200 bg-white p-3"
              >
                <div className="text-xs font-semibold text-navy-600">
                  {c.circular_number}
                  {c.section_reference && ` — ${c.section_reference}`}
                </div>
                <p className="mt-1 text-xs italic text-gray-600">
                  &ldquo;{c.verbatim_quote}&rdquo;
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended actions */}
      {q.recommended_actions && q.recommended_actions.length > 0 && (
        <div className="mb-8">
          <h3 className="mb-2 text-sm font-semibold text-gray-700">
            Recommended Actions
          </h3>
          <div className="space-y-2">
            {q.recommended_actions.map((a, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3"
              >
                <Badge variant={impactVariant(a.priority)}>{a.priority}</Badge>
                <div>
                  <div className="text-xs font-medium text-gray-500">
                    {a.team}
                  </div>
                  <div className="text-sm text-gray-700">{a.action_text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feedback + Share */}
      <div className="border-t border-gray-200 pt-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-700">
              Was this helpful?
            </h3>
            <div className="flex gap-3">
              <button
                onClick={() =>
                  feedbackMutation.mutate({ questionId: id, feedback: 1 })
                }
                disabled={q.feedback !== null}
                className={`rounded-lg border px-4 py-2 text-sm ${
                  q.feedback === 1
                    ? "border-green-300 bg-green-50 text-green-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                } disabled:cursor-not-allowed`}
              >
                &#128077; Yes
              </button>
              <button
                onClick={() =>
                  feedbackMutation.mutate({ questionId: id, feedback: -1 })
                }
                disabled={q.feedback !== null}
                className={`rounded-lg border px-4 py-2 text-sm ${
                  q.feedback === -1
                    ? "border-red-300 bg-red-50 text-red-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                } disabled:cursor-not-allowed`}
              >
                &#128078; No
              </button>
            </div>
          </div>

          <button
            onClick={() => {
              trackEvent("share_snippet_dialog_opened", { question_id: id });
              setShareOpen(true);
            }}
            className="inline-flex items-center gap-2 rounded-lg border border-navy-300 bg-white px-4 py-2 text-sm font-medium text-navy-700 hover:bg-navy-50 dark:border-navy-600 dark:bg-gray-900 dark:text-navy-200 dark:hover:bg-navy-900/40"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
              />
            </svg>
            Share
          </button>
        </div>
      </div>

      <ShareSnippetDialog
        questionId={id}
        open={shareOpen}
        onClose={() => setShareOpen(false)}
      />
    </div>
  );
}
