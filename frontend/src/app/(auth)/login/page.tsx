/**
 * Login page — email input → OTP sent.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { loginUser, type LoginRequest } from "@/lib/api/auth";
import { type AxiosError } from "axios";
import type { ApiError } from "@/lib/api/auth";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");

  const mutation = useMutation<unknown, AxiosError<ApiError>, LoginRequest>({
    mutationFn: loginUser,
    onSuccess: () => {
      const params = new URLSearchParams({
        email,
        purpose: "login",
      });
      router.push(`/verify?${params.toString()}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({ email });
  };

  const errorMsg = mutation.error?.response?.data?.error || mutation.error?.message;

  return (
    <>
      <h2 className="mb-6 text-center text-xl font-semibold text-gray-800">Welcome back</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">
            Work Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            autoFocus
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm
              focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-200"
          />
        </div>

        {errorMsg && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{errorMsg}</div>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full rounded-lg bg-navy-600 px-4 py-2.5 text-sm font-medium text-white
            transition-colors hover:bg-navy-700
            disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          {mutation.isPending ? "Sending OTP..." : "Send OTP"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-500">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="font-medium text-navy-600 hover:text-navy-800">
          Register
        </Link>
      </p>
    </>
  );
}
