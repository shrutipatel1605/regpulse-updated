/**
 * Typed API client for all 5 auth endpoints.
 *
 * Endpoints:
 *   POST /auth/register    → MessageResponse
 *   POST /auth/login       → MessageResponse
 *   POST /auth/verify-otp  → AuthResponse
 *   POST /auth/refresh     → AuthResponse
 *   POST /auth/logout      → MessageResponse
 */

import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Request types (mirrors backend/app/schemas/auth.py)
// ---------------------------------------------------------------------------

export interface RegisterRequest {
  email: string;
  full_name: string;
  designation?: string | null;
  org_name?: string | null;
  org_type?: string | null;
  honeypot?: string;
}

export interface LoginRequest {
  email: string;
}

export interface OTPVerifyRequest {
  email: string;
  otp: string;
  purpose: "register" | "login";
  full_name?: string | null;
  designation?: string | null;
  org_name?: string | null;
  org_type?: string | null;
}

// Deprecated: RefreshTokenRequest removed because refresh_token is now an HTTPOnly cookie

// ---------------------------------------------------------------------------
// Response types (mirrors backend/app/schemas/auth.py)
// ---------------------------------------------------------------------------

export interface UserResponse {
  id: string;
  email: string;
  email_verified: boolean;
  full_name: string;
  designation: string | null;
  org_name: string | null;
  org_type: string | null;
  credit_balance: number;
  plan: string;
  plan_expires_at: string | null;
  plan_auto_renew: boolean;
  is_admin: boolean;
  last_login_at: string | null;
  last_seen_updates: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  success: boolean;
  user: UserResponse;
  tokens: TokenResponse;
}

export interface MessageResponse {
  success: boolean;
  message: string;
}

export interface ApiError {
  success: false;
  error: string;
  code: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function registerUser(data: RegisterRequest): Promise<MessageResponse> {
  const res = await api.post<MessageResponse>("/auth/register", data);
  return res.data;
}

export async function loginUser(data: LoginRequest): Promise<MessageResponse> {
  const res = await api.post<MessageResponse>("/auth/login", data);
  return res.data;
}

export async function verifyOtp(data: OTPVerifyRequest): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/verify-otp", data);
  return res.data;
}

export async function refreshToken(): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/refresh");
  return res.data;
}

export async function logoutUser(): Promise<MessageResponse> {
  const res = await api.post<MessageResponse>("/auth/logout");
  return res.data;
}
