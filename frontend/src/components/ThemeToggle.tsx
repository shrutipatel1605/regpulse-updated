"use client";

import { useEffect, useState } from "react";
import { useThemeStore } from "@/stores/themeStore";
import { trackEvent } from "@/lib/analytics";
import { cn } from "@/lib/cn";

interface ThemeToggleProps {
  className?: string;
}

/**
 * Two-state toggle (light / dark). The button defers to `useThemeStore`
 * for the actual theme switch and emits `dark_mode_toggled` for analytics.
 *
 * Render is suppressed until after mount to avoid a hydration mismatch:
 * the server sees the default `light` state, but the pre-hydration script
 * may have already flipped <html> to `dark`.
 */
export function ThemeToggle({ className }: ThemeToggleProps) {
  const theme = useThemeStore((s) => s.theme);
  const toggle = useThemeStore((s) => s.toggle);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    // Reserve the same footprint to keep the sidebar layout stable.
    return (
      <div
        className={cn(
          "h-9 w-full rounded-lg border border-gray-200 dark:border-gray-800",
          className,
        )}
        aria-hidden="true"
      />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={() => {
        const next = isDark ? "light" : "dark";
        toggle();
        trackEvent("dark_mode_toggled", { to: next });
      }}
      aria-pressed={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={cn(
        "flex w-full items-center justify-between gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-900",
        className,
      )}
    >
      <span>{isDark ? "Dark mode" : "Light mode"}</span>
      <span className="relative inline-flex h-5 w-9 items-center rounded-full bg-gray-200 transition-colors dark:bg-navy-600">
        <span
          className={cn(
            "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform",
            isDark ? "translate-x-4" : "translate-x-0.5",
          )}
        />
      </span>
    </button>
  );
}
