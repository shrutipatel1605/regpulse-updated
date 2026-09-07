"use client";

import { cn } from "@/lib/cn";

type BadgeVariant = "default" | "high" | "medium" | "low" | "active" | "superseded" | "draft";

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-700",
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-green-100 text-green-700",
  active: "bg-emerald-100 text-emerald-700",
  superseded: "bg-gray-200 text-gray-500",
  draft: "bg-blue-100 text-blue-700",
};

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Map impact level string to Badge variant. */
export function impactVariant(level: string | null): BadgeVariant {
  if (!level) return "default";
  switch (level.toUpperCase()) {
    case "HIGH":
      return "high";
    case "MEDIUM":
      return "medium";
    case "LOW":
      return "low";
    default:
      return "default";
  }
}

/** Map status string to Badge variant. */
export function statusVariant(status: string): BadgeVariant {
  switch (status.toUpperCase()) {
    case "ACTIVE":
      return "active";
    case "SUPERSEDED":
      return "superseded";
    case "DRAFT":
      return "draft";
    default:
      return "default";
  }
}
