/**
 * Thin wrapper around posthog-js so feature code doesn't need to import it
 * directly. Safe to call before posthog.init() — calls are dropped silently
 * (this matters during SSR / when NEXT_PUBLIC_POSTHOG_KEY is unset).
 */
import posthog from "posthog-js";

type EventName =
  | "confidence_meter_viewed"
  | "dark_mode_toggled"
  | "share_snippet_dialog_opened"
  | "ask_question_submitted";

export function trackEvent(
  name: EventName,
  properties?: Record<string, unknown>,
): void {
  if (typeof window === "undefined") return;
  if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return;
  try {
    posthog.capture(name, properties);
  } catch {
    // PostHog isn't a critical path; never break the UI on a capture error.
  }
}

/**
 * Read a typed feature flag. Returns `defaultValue` until PostHog has
 * loaded the user's flag payload, so callers should treat the first
 * render as the control branch.
 */
export function getFeatureFlag<T extends string | boolean>(
  key: string,
  defaultValue: T,
): T {
  if (typeof window === "undefined") return defaultValue;
  if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return defaultValue;
  try {
    const value = posthog.getFeatureFlag(key);
    if (value === undefined || value === null) return defaultValue;
    return value as T;
  } catch {
    return defaultValue;
  }
}
