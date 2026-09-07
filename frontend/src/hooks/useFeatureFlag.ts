"use client";

import { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";

/**
 * Subscribe to a PostHog feature flag with a typed default.
 *
 * Usage:
 * ```ts
 * const variant = useFeatureFlag<"control" | "v2">("ask_layout", "control");
 * ```
 *
 * Behaviour:
 * - Returns `defaultValue` on the server and during the very first
 *   client render so the markup matches the SSR output (no hydration
 *   mismatch).
 * - Re-renders when PostHog finishes loading the user's flag payload
 *   or when an admin pushes a flag change.
 * - Returns `defaultValue` if PostHog isn't initialised (e.g. when
 *   `NEXT_PUBLIC_POSTHOG_KEY` isn't set in DEMO_MODE).
 */
export function useFeatureFlag<T extends string | boolean>(
  key: string,
  defaultValue: T,
): T {
  const posthog = usePostHog();
  const [value, setValue] = useState<T>(defaultValue);

  useEffect(() => {
    if (!posthog) return;

    const read = (): T => {
      try {
        const raw = posthog.getFeatureFlag(key);
        if (raw === undefined || raw === null) return defaultValue;
        return raw as T;
      } catch {
        return defaultValue;
      }
    };

    setValue(read());

    // Re-read whenever PostHog refreshes its flag payload (initial load,
    // user identify, or remote update). The unsubscribe shape varies
    // between posthog-js versions; tolerate either return.
    const unsub = posthog.onFeatureFlags?.(() => setValue(read()));
    return () => {
      if (typeof unsub === "function") unsub();
    };
  }, [posthog, key, defaultValue]);

  return value;
}
