/**
 * Zustand auth store.
 *
 * Access token stored in memory (Zustand) — NOT localStorage.
 * Refresh token is stored via backend httpOnly cookie.
 */

import { create } from "zustand";
import type { UserResponse } from "@/lib/api/auth";
import { logoutUser, refreshToken as refreshTokenApi } from "@/lib/api/auth";

interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  isAuthenticated: boolean;

  /** Set auth state after login / verify-otp / refresh. */
  setAuth: (user: UserResponse, accessToken: string) => void;

  /** Clear all auth state (local only — does not call API). */
  clearAuth: () => void;

  /** Full logout: call API, then clear state. */
  logout: () => Promise<void>;

  /** Attempt silent refresh. Returns new access token or null. */
  silentRefresh: () => Promise<string | null>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,

  setAuth: (user, accessToken) => {
    set({
      user,
      accessToken,
      isAuthenticated: true,
    });
  },

  clearAuth: () => {
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
    });
  },

  logout: async () => {
    // Clear state immediately so UI reflects logged-out
    get().clearAuth();
    try {
      await logoutUser();
    } catch {
      // Logout is idempotent — ignore errors
    }
  },

  silentRefresh: async () => {
    try {
      const res = await refreshTokenApi();
      set({
        user: res.user,
        accessToken: res.tokens.access_token,
        isAuthenticated: true,
      });
      return res.tokens.access_token;
    } catch {
      // Refresh failed — force logout
      get().clearAuth();
      return null;
    }
  },
}));
