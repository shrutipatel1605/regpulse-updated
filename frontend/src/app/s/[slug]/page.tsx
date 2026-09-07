/**
 * Public snippet page — /s/[slug]
 *
 * Server component (no auth, no client state). Fetches the redacted
 * snippet from the backend, renders the safe preview, and pushes a
 * registration CTA. The full detailed_interpretation never reaches this
 * file because it never leaves backend/app/services/snippet_service.py.
 *
 * Open Graph metadata is generated from the snippet so LinkedIn/X show
 * a rich preview when the link is shared.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchPublicSnippet } from "@/lib/api/snippets";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const snippet = await fetchPublicSnippet(slug);

  if (!snippet) {
    return { title: "Snippet not found — RegPulse" };
  }

  const title = snippet.consult_expert
    ? "RegPulse — Compliance question requires expert review"
    : "RegPulse — RBI compliance answer";
  const description = snippet.snippet_text.slice(0, 200);

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      images: [{ url: snippet.og_image_url, width: 1200, height: 630 }],
      type: "article",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [snippet.og_image_url],
    },
  };
}

export default async function PublicSnippetPage({ params }: PageProps) {
  const { slug } = await params;
  const snippet = await fetchPublicSnippet(slug);

  if (!snippet) {
    notFound();
  }

  const registerUrl = `/register?utm_source=share&utm_medium=snippet&slug=${slug}`;

  return (
    <main className="min-h-screen bg-gradient-to-b from-navy-900 to-navy-700 px-6 py-12 text-white">
      <div className="mx-auto max-w-2xl">
        {/* Brand header */}
        <Link href="/" className="mb-8 inline-block">
          <h1 className="text-3xl font-bold text-blue-300">RegPulse</h1>
          <p className="text-xs uppercase tracking-wider text-blue-200">
            RBI Regulatory Intelligence
          </p>
        </Link>

        {/* Snippet card */}
        <article className="rounded-xl border border-blue-400/30 bg-white/5 p-8 backdrop-blur">
          {snippet.consult_expert ? (
            <div className="mb-4 inline-block rounded-full bg-amber-500/20 px-3 py-1 text-xs font-semibold uppercase text-amber-300">
              ⚠ Consult an Expert
            </div>
          ) : (
            <div className="mb-4 inline-block rounded-full bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase text-blue-300">
              Compliance Answer Preview
            </div>
          )}

          <p className="text-lg leading-relaxed text-white">
            {snippet.snippet_text}
          </p>

          {snippet.top_citation && (
            <div className="mt-6 border-t border-blue-400/20 pt-4">
              <div className="text-xs font-semibold uppercase text-blue-300">
                Source
              </div>
              <div className="mt-1 text-sm font-medium text-white">
                {snippet.top_citation.circular_number}
                {snippet.top_citation.section_reference && (
                  <span className="text-blue-200">
                    {" "}
                    — Section {snippet.top_citation.section_reference}
                  </span>
                )}
              </div>
              <p className="mt-2 text-sm italic text-blue-100">
                &ldquo;{snippet.top_citation.verbatim_quote}&rdquo;
              </p>
            </div>
          )}
        </article>

        {/* CTA */}
        <div className="mt-8 rounded-xl border border-blue-400/30 bg-blue-500/10 p-6 text-center backdrop-blur">
          <h2 className="text-xl font-bold text-white">
            Get the full compliance answer
          </h2>
          <p className="mt-2 text-sm text-blue-100">{snippet.register_cta}</p>
          <Link
            href={registerUrl}
            className="mt-4 inline-block rounded-lg bg-blue-500 px-6 py-3 text-sm font-bold text-white hover:bg-blue-400"
          >
            Register on RegPulse →
          </Link>
        </div>

        <p className="mt-8 text-center text-xs text-blue-200">
          RegPulse runs every answer through a 3-layer anti-hallucination
          pipeline. Sources are verified against official RBI circulars.
        </p>
      </div>
    </main>
  );
}
