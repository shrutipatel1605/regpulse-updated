"use client";

import { cn } from "@/lib/cn";

interface SkeletonProps {
  className?: string;
  /** Render an aria-busy region wrapper. Default: true. */
  ariaLabel?: string;
}

/**
 * Plain rectangular skeleton block. Use this directly for one-off
 * placeholders, or compose into the helpers below for list rows.
 */
export function Skeleton({ className, ariaLabel }: SkeletonProps) {
  return (
    <div
      role={ariaLabel ? "status" : undefined}
      aria-label={ariaLabel}
      aria-busy={ariaLabel ? true : undefined}
      className={cn(
        "animate-pulse rounded-md bg-gray-200/80 dark:bg-gray-800",
        className,
      )}
    />
  );
}

interface ListSkeletonProps {
  rows?: number;
  className?: string;
}

/** Skeleton for the library / updates / history card list rows. */
export function CardListSkeleton({ rows = 6, className }: ListSkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading"
      className={cn("space-y-3", className)}
    >
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
        >
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-12" />
          </div>
          <Skeleton className="mt-3 h-4 w-full" />
          <Skeleton className="mt-2 h-4 w-3/4" />
          <div className="mt-3 flex gap-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
      ))}
    </div>
  );
}
