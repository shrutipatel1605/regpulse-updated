"use client";

import { useState } from "react";
import { createSnippet, type PublicSnippetResponse } from "@/lib/api/snippets";

interface Props {
  questionId: string;
  open: boolean;
  onClose: () => void;
}

export function ShareSnippetDialog({ questionId, open, onClose }: Props) {
  const [snippet, setSnippet] = useState<PublicSnippetResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (!open) return null;

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await createSnippet(questionId);
      setSnippet(result);
    } catch (e) {
      const msg =
        e && typeof e === "object" && "message" in e
          ? String((e as { message: unknown }).message)
          : "Failed to create snippet";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!snippet) return;
    await navigator.clipboard.writeText(snippet.share_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const linkedinShare = snippet
    ? `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(snippet.share_url)}`
    : "#";
  const xShare = snippet
    ? `https://twitter.com/intent/tweet?url=${encodeURIComponent(
        snippet.share_url,
      )}&text=${encodeURIComponent("RegPulse — RBI compliance answer")}`
    : "#";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Share this answer</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {!snippet && !loading && (
          <>
            <p className="mb-4 text-sm text-gray-600">
              Create a public, redacted preview of this answer. The full
              detailed answer is never shared — viewers see a quick summary
              and one citation, with a prompt to register for the full
              compliance brief.
            </p>
            <button
              onClick={handleCreate}
              className="w-full rounded-lg bg-navy-600 px-4 py-2 text-sm font-medium text-white hover:bg-navy-700"
            >
              Generate share link
            </button>
          </>
        )}

        {loading && (
          <div className="py-8 text-center text-sm text-gray-500">
            Generating safe snippet…
          </div>
        )}

        {error && (
          <div className="mt-2 rounded border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            {error}
          </div>
        )}

        {snippet && (
          <div className="space-y-4">
            <div className="rounded-lg border border-navy-100 bg-navy-50 p-3">
              <div className="text-xs font-semibold uppercase text-navy-600">
                Preview
              </div>
              <p className="mt-1 text-sm text-gray-800">{snippet.snippet_text}</p>
              {snippet.top_citation && (
                <div className="mt-2 text-xs text-gray-500">
                  Source: {snippet.top_citation.circular_number}
                </div>
              )}
              {snippet.consult_expert && (
                <div className="mt-2 text-xs font-medium text-amber-700">
                  ⚠ Consult Expert fallback
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={snippet.share_url}
                className="flex-1 rounded border border-gray-300 bg-gray-50 px-3 py-2 text-xs text-gray-700"
                onClick={(e) => (e.target as HTMLInputElement).select()}
              />
              <button
                onClick={handleCopy}
                className="rounded bg-navy-600 px-3 py-2 text-xs font-medium text-white hover:bg-navy-700"
              >
                {copied ? "Copied" : "Copy"}
              </button>
            </div>

            <div className="flex gap-2">
              <a
                href={linkedinShare}
                target="_blank"
                rel="noreferrer"
                className="flex-1 rounded border border-gray-300 bg-white px-3 py-2 text-center text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Share on LinkedIn
              </a>
              <a
                href={xShare}
                target="_blank"
                rel="noreferrer"
                className="flex-1 rounded border border-gray-300 bg-white px-3 py-2 text-center text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Share on X
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
