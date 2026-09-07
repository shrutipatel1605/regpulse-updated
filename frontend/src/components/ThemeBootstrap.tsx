"use client";

import { useApplyTheme } from "@/stores/themeStore";

/**
 * Mount-once component that wires the theme store's `useApplyTheme` hook
 * into the React tree. Renders nothing — it exists purely for the side
 * effect of applying the persisted/system theme on hydration and
 * listening for OS preference changes.
 */
export function ThemeBootstrap() {
  useApplyTheme();
  return null;
}
