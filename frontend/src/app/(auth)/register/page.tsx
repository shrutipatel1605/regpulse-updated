/**
 * Registration page — work email + profile info → OTP sent.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { registerUser, type RegisterRequest } from "@/lib/api/auth";
import { type AxiosError } from "axios";
import type { ApiError } from "@/lib/api/auth";
import Link from "next/link";

const ORG_TYPES = [
  { value: "BANK", label: "Bank" },
  { value: "NBFC", label: "NBFC" },
  { value: "COOPERATIVE", label: "Cooperative Bank" },
  { value: "PAYMENT_BANK", label: "Payment Bank" },
  { value: "SMALL_FINANCE_BANK", label: "Small Finance Bank" },
  { value: "FINTECH", label: "Fintech" },
  { value: "INSURANCE", label: "Insurance" },
  { value: "OTHER", label: "Other" },
];

export default function RegisterPage() {
  const router = useRouter();

  const [form, setForm] = useState<RegisterRequest>({
    email: "",
    full_name: "",
    designation: "",
    org_name: "",
    org_type: "",
    honeypot: "",
  });

  const mutation = useMutation<unknown, AxiosError<ApiError>, RegisterRequest>({
    mutationFn: registerUser,
    onSuccess: () => {
      // Navigate to OTP verification with context
      const params = new URLSearchParams({
        email: form.email,
        purpose: "register",
      });
      router.push(`/verify?${params.toString()}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(form);
  };

  const errorMsg = mutation.error?.response?.data?.error || mutation.error?.message;

  return (
    <>
      <h2 className="mb-6 text-center text-xl font-semibold text-gray-800">Create your account</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Honeypot — hidden from real users, bots fill it */}
        <input
          type="text"
          name="honeypot"
          value={form.honeypot}
          onChange={(e) => setForm({ ...form, honeypot: e.target.value })}
          className="absolute -left-[9999px] h-0 w-0"
          tabIndex={-1}
          autoComplete="off"
          aria-hidden="true"
        />

        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">
            Work Email <span className="text-red-500">*</span>
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@company.com"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm
              focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-200"
          />
        </div>

        <div>
          <label htmlFor="full_name" className="mb-1 block text-sm font-medium text-gray-700">
            Full Name <span className="text-red-500">*</span>
          </label>
          <input
            id="full_name"
            type="text"
            required
            autoComplete="name"
            placeholder="Amit Sharma"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm
              focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-200"
          />
        </div>

        <div>
          <label htmlFor="designation" className="mb-1 block text-sm font-medium text-gray-700">
            Designation
          </label>
          <input
            id="designation"
            type="text"
            autoComplete="organization-title"
            placeholder="Chief Compliance Officer"
            value={form.designation || ""}
            onChange={(e) => setForm({ ...form, designation: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm
              focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-200"
          />
        </div>

        <div>
          <label htmlFor="org_name" className="mb-1 block text-sm font-medium text-gray-700">
            Organisation Name
          </label>
          <input
            id="org_name"
            type="text"
            autoComplete="organization"
            placeholder="HDFC Bank"
            value={form.org_name || ""}
            onChange={(e) => setForm({ ...form, org_name: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm
              focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-200"
          />
        </div>

        <div>
          <label htmlFor="org_type" className="mb-1 block text-sm font-medium text-gray-700">
            Organisation Type
          </label>
          <select
            id="org_type"
            value={form.org_type || ""}
            onChange={(e) => setForm({ ...form, org_type: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm
              focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-200"
          >
            <option value="">Select type...</option>
            {ORG_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
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
          {mutation.isPending ? "Sending OTP..." : "Register with Work Email"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-500">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-navy-600 hover:text-navy-800">
          Log in
        </Link>
      </p>
    </>
  );
}
