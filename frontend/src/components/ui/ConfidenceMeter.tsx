"use client";

import { cn } from "@/lib/cn";

export type ConfidenceBand = "high" | "medium" | "low" | "fallback";

interface ConfidenceMeterProps {
  /** 0.0–1.0. `null` means the question pre-dates Sprint 4 persistence. */
  score: number | null;
  /** When true the LLM was bypassed for the "Consult an Expert" fallback. */
  consultExpert: boolean;
  /** Compact variant — used inside list items. */
  compact?: boolean;
  className?: string;
}

/**
 * Compute the band from a confidence score. The thresholds match
 * `llm_service._compute_confidence` semantics: < 0.5 already triggers
 * the consult-expert fallback in the backend, so any score below that
 * here is paired with `consultExpert=true` from the API.
 */
export function bandFor(
  score: number | null,
  consultExpert: boolean,
): ConfidenceBand {
  if (consultExpert) return "fallback";
  if (score === null) return "medium";
  if (score >= 0.8) return "high";
  if (score >= 0.65) return "medium";
  return "low";
}

const bandLabel: Record<ConfidenceBand, string> = {
  high: "High confidence",
  medium: "Moderate confidence",
  low: "Low confidence",
  fallback: "Consult an expert",
};

// WCAG-AA: every text colour below has ≥ 4.5:1 contrast against the
// fill colour AND its dark-mode counterpart.
const bandFill: Record<ConfidenceBand, string> = {
  high: "bg-emerald-500 dark:bg-emerald-400",
  medium: "bg-amber-500 dark:bg-amber-400",
  low: "bg-orange-500 dark:bg-orange-400",
  fallback: "bg-rose-500 dark:bg-rose-400",
};

const bandText: Record<ConfidenceBand, string> = {
  high: "text-emerald-700 dark:text-emerald-200",
  medium: "text-amber-700 dark:text-amber-200",
  low: "text-orange-700 dark:text-orange-200",
  fallback: "text-rose-700 dark:text-rose-200",
};

const bandRing: Record<ConfidenceBand, string> = {
  high: "border-emerald-200 dark:border-emerald-700",
  medium: "border-amber-200 dark:border-amber-700",
  low: "border-orange-200 dark:border-orange-700",
  fallback: "border-rose-200 dark:border-rose-700",
};

const bandTint: Record<ConfidenceBand, string> = {
  high: "bg-emerald-50 dark:bg-emerald-900/30",
  medium: "bg-amber-50 dark:bg-amber-900/30",
  low: "bg-orange-50 dark:bg-orange-900/30",
  fallback: "bg-rose-50 dark:bg-rose-900/30",
};

export function ConfidenceMeter({
  score,
  consultExpert,
  compact = false,
  className,
}: ConfidenceMeterProps) {
  // Pre-Sprint-4 questions have no score and no fallback. Render nothing
  // rather than misrepresent the answer with a fake number.
  if (score === null && !consultExpert) return null;

  const band = bandFor(score, consultExpert);
  const displayScore = consultExpert ? 0 : score ?? 0;
  const pct = Math.round(displayScore * 100);

  if (compact) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
          bandTint[band],
          bandRing[band],
          bandText[band],
          className,
        )}
        aria-label={`${bandLabel[band]} ${consultExpert ? "" : `(${pct}%)`}`}
      >
        <span
          className={cn("h-1.5 w-1.5 rounded-full", bandFill[band])}
          aria-hidden="true"
        />
        {consultExpert ? "Consult expert" : `${pct}%`}
      </span>
    );
  }

  return (
    <section
      className={cn(
        "rounded-lg border p-4",
        bandTint[band],
        bandRing[band],
        className,
      )}
      aria-label="Answer confidence"
      role="group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={cn("text-xs font-semibold uppercase", bandText[band])}
          >
            {bandLabel[band]}
          </span>
        </div>
        {!consultExpert && (
          <span className={cn("text-sm font-semibold tabular-nums", bandText[band])}>
            {pct}%
          </span>
        )}
      </div>

      <div
        className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/60 dark:bg-black/30"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={cn("h-full rounded-full transition-all", bandFill[band])}
          style={{ width: consultExpert ? "100%" : `${pct}%` }}
        />
      </div>

      <p className={cn("mt-2 text-xs leading-relaxed", bandText[band])}>
        {consultExpert
          ? "RegPulse could not find sufficient evidence in the indexed RBI circulars. Validate this answer with your Chief Compliance Officer before acting."
          : band === "high"
            ? "Strong citation coverage and direct support from the retrieved circulars."
            : band === "medium"
              ? "Reasonable support from circulars, but some signals were weaker. Verify the citations."
              : "Limited citation coverage. Treat as preliminary and confirm with expert review."}
      </p>
    </section>
  );
}
