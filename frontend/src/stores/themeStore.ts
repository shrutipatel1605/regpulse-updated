/**
 * Theme store — light/dark mode preference.
 *
 * Persistence: an explicit user choice is written to localStorage so it
 * survives page reloads. When no explicit choice has been made the store
 * reflects the OS preference (`prefers-color-scheme: dark`).
 *
 * The store does NOT touch the DOM directly — `ThemeBootstrap` and the
 * `useApplyTheme` hook take care of toggling the `dark` class on <html>.
 * Tailwind reads that class via the `darkMode: "class"` config.
 */

import { useEffect } from "react";
import { create } from "zustand";

export type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  /** True only when the user picked a theme explicitly. */
  hasExplicitChoice: boolean;
  setTheme: (theme: Theme) => void;
  toggle: () => void;
  /** Adopt the OS preference, clearing any explicit choice. */
  resetToSystem: () => void;
}

const STORAGE_KEY = "regpulse:theme";

function readStoredTheme(): { theme: Theme; explicit: boolean } {
  if (typeof window === "undefined") {
    return { theme: "light", explicit: false };
  }
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") {
      return { theme: stored, explicit: true };
    }
  } catch {
    // localStorage may be blocked (private mode) — fall through to system.
  }
  const prefersDark =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  return { theme: prefersDark ? "dark" : "light", explicit: false };
}

function applyThemeToDOM(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
  // Helps native form controls + scrollbars match.
  root.style.colorScheme = theme;
}

const initial = readStoredTheme();

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: initial.theme,
  hasExplicitChoice: initial.explicit,

  setTheme: (theme) => {
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(STORAGE_KEY, theme);
      } catch {
        /* ignore */
      }
    }
    applyThemeToDOM(theme);
    set({ theme, hasExplicitChoice: true });
  },

  toggle: () => {
    const next = get().theme === "dark" ? "light" : "dark";
    get().setTheme(next);
  },

  resetToSystem: () => {
    if (typeof window !== "undefined") {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch {
        /* ignore */
      }
    }
    const fresh = readStoredTheme();
    applyThemeToDOM(fresh.theme);
    set({ theme: fresh.theme, hasExplicitChoice: false });
  },
}));

/**
 * Side-effect hook that (a) applies the current theme to <html> on mount
 * and (b) listens for OS preference changes when no explicit choice is set.
 * Mount once at the root layout.
 */
export function useApplyTheme(): void {
  const theme = useThemeStore((s) => s.theme);
  const hasExplicitChoice = useThemeStore((s) => s.hasExplicitChoice);

  useEffect(() => {
    applyThemeToDOM(theme);
  }, [theme]);

  useEffect(() => {
    if (hasExplicitChoice) return;
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      const next: Theme = e.matches ? "dark" : "light";
      applyThemeToDOM(next);
      useThemeStore.setState({ theme: next, hasExplicitChoice: false });
    };
    media.addEventListener("change", handler);
    return () => media.removeEventListener("change", handler);
  }, [hasExplicitChoice]);
}
