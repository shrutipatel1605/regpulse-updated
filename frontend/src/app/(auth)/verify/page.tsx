/**
 * OTP verification page — 6 individual digit boxes.
 *
 * - Auto-advances on input, auto-submits on last digit.
 * - On success: stores tokens in Zustand (memory), redirects to dashboard.
 */

"use client";

import { useState, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { verifyOtp, type OTPVerifyRequest, type AuthResponse } from "@/lib/api/auth";
import { type AxiosError } from "axios";
import type { ApiError } from "@/lib/api/auth";
import { useAuthStore } from "@/stores/authStore";
import OTPInput from "@/components/OTPInput";

function VerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((s) => s.setAuth);

  const email = searchParams.get("email") || "";
  const purpose = (searchParams.get("purpose") || "login") as "register" | "login";

  const [otp, setOtp] = useState("");

  const mutation = useMutation<AuthResponse, AxiosError<ApiError>, OTPVerifyRequest>({
    mutationFn: verifyOtp,
    onSuccess: (data) => {
      setAuth(data.user, data.tokens.access_token);
      router.push("/dashboard");
    },
  });

  const handleComplete = useCallback(
    (completedOtp: string) => {
      if (mutation.isPending) return;
      mutation.mutate({ email, otp: completedOtp, purpose });
    },
    [email, purpose, mutation],
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length === 6) {
      handleComplete(otp);
    }
  };

  const errorMsg = mutation.error?.response?.data?.error || mutation.error?.message;

  // Mask email for display: a***@domain.com
  const maskedEmail = email
    ? `${email[0]}${"*".repeat(Math.max(0, email.indexOf("@") - 1))}${email.slice(email.indexOf("@"))}`
    : "";

  return (
    <>
      <h2 className="mb-2 text-center text-xl font-semibold text-gray-800">
        Enter verification code
      </h2>
      <p className="mb-8 text-center text-sm text-gray-500">
        We sent a 6-digit code to <span className="font-medium text-gray-700">{maskedEmail}</span>
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <OTPInput
          value={otp}
          onChange={setOtp}
          onComplete={handleComplete}
          disabled={mutation.isPending}
        />

        {errorMsg && (
          <div className="rounded-md bg-red-50 p-3 text-center text-sm text-red-700">
            {errorMsg}
          </div>
        )}

        <button
          type="submit"
          disabled={mutation.isPending || otp.length < 6}
          className="w-full rounded-lg bg-navy-600 px-4 py-2.5 text-sm font-medium text-white
            transition-colors hover:bg-navy-700
            disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          {mutation.isPending ? "Verifying..." : "Verify OTP"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-500">
        Didn&apos;t receive the code?{" "}
        <button
          type="button"
          onClick={() => router.back()}
          className="font-medium text-navy-600 hover:text-navy-800"
        >
          Try again
        </button>
      </p>
    </>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="py-12 text-center text-gray-400">Loading...</div>}>
      <VerifyContent />
    </Suspense>
  );
}
